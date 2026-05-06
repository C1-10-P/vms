from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from apps.core.models.academic import Class
from apps.core import models
from .models import AccessZone, AccessLog, TwoFactorSession
from .services import AccessControlService
from apps.access.models.permission import AccessPermission
from apps.access.models.geofence import GeofenceBoundary
from apps.access.forms import AccessZoneForm, AccessPermissionModalForm, AccessPermission, GeofenceModalForm
from apps.core.models import Institution, Department, Person, Staff, College, School, Program


# ============ Classroom/Access Zone CRUD Views ============

class ZoneListView(LoginRequiredMixin, ListView):
    """List all access zones/classrooms"""
    model = AccessZone
    ordering = ['-created_at']
    template_name = 'access/zone_list.html'
    context_object_name = 'zones'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AccessZone.objects.filter(is_active=True).select_related('institution', 'parent_zone')
        
        # Filter by zone type
        zone_type = self.request.GET.get('zone_type')
        if zone_type:
            queryset = queryset.filter(zone_type=zone_type)
        
        # Filter by institution
        institution_id = self.request.GET.get('institution_id')
        if institution_id:
            queryset = queryset.filter(institution_id=institution_id)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(building__icontains=search) |
                Q(room_number__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zone_types'] = AccessZone.ZoneType.choices
        context['institutions'] = Institution.objects.filter(is_active=True)
        context['total_zones'] = AccessZone.objects.filter(is_active=True).count()
        context['classrooms'] = AccessZone.objects.filter(zone_type='classroom', is_active=True).count()
        context['labs'] = AccessZone.objects.filter(zone_type='lab', is_active=True).count()
        return context


class ZoneDetailView(LoginRequiredMixin, DetailView):
    """Zone/Classroom detail view"""
    model = AccessZone
    template_name = 'access/zone_detail.html'
    context_object_name = 'zone'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get permissions for this zone
        context['permissions'] = self.object.permissions.filter(is_active=True)
        
        # Get recent access logs
        context['recent_logs'] = AccessLog.objects.filter(
            zone=self.object
        ).select_related('person').order_by('-access_time')[:20]
        
        # Get statistics
        from datetime import timedelta
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        context['today_access'] = AccessLog.objects.filter(
            zone=self.object,
            access_time__date=today
        ).count()
        
        context['week_access'] = AccessLog.objects.filter(
            zone=self.object,
            access_time__date__gte=week_ago
        ).count()
        
        context['successful_today'] = AccessLog.objects.filter(
            zone=self.object,
            access_time__date=today,
            result='granted'
        ).count()
        
        context['denied_today'] = AccessLog.objects.filter(
            zone=self.object,
            access_time__date=today,
            result='denied'
        ).count()
        
        # Get geofence if exists
        context['geofence'] = GeofenceBoundary.objects.filter(zone=self.object).first()
        
        # Get child zones
        context['child_zones'] = self.object.child_zones.filter(is_active=True)
        
        # Get occupancy percentage
        if self.object.capacity > 0:
            context['occupancy_percentage'] = (self.object.current_occupancy / self.object.capacity) * 100
        else:
            context['occupancy_percentage'] = 0
        
        return context


class ZoneCreateView(LoginRequiredMixin, CreateView):
    model = AccessZone
    form = AccessZoneForm
    fields = ['name', 'code', 'zone_type', 'parent_zone', 'institution', 'college',
              'school', 'department', 'access_level', 'requires_2fa', 'building',
              'floor', 'room_number', 'capacity', 'description']
    template_name = 'access/zone_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Zone/Classroom'
        context['zone_types'] = AccessZone.ZoneType.choices
        context['institutions'] = Institution.objects.filter(is_active=True)
        context['institutions'] = College.objects.filter(is_active=True)
        context['institutions'] = School.objects.filter(is_active=True)
        context['institutions'] = Department.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Zone {form.instance.name} created successfully.'})
        messages.success(self.request, f'Zone {form.instance.name} created successfully.')
        return response
    
    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({'success': False, 'error': errors}, status=400)
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('access:zone_list')


class ZoneUpdateView(LoginRequiredMixin, UpdateView):
    """Update zone/classroom"""
    model = AccessZone
    fields = ['name', 'code', 'zone_type', 'parent_zone', 'access_level', 'requires_2fa',
              'building', 'floor', 'room_number', 'capacity', 'description']
    template_name = 'access/edit_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Zone: {self.object.name}'
        context['zone_types'] = AccessZone.ZoneType.choices
        return context
    
    def get_success_url(self):
        return reverse_lazy('access:zone_detail', kwargs={'pk': self.object.pk})


class ZoneDeleteView(LoginRequiredMixin, DeleteView):
    """Delete zone/classroom (soft delete)"""
    model = AccessZone
    template_name = 'access/zone_confirm_delete.html'
    success_url = reverse_lazy('access:zone_list')
    
    def delete(self, request, *args, **kwargs):
        zone = self.get_object()
        zone.soft_delete()
        messages.success(request, f'Zone {zone.name} has been archived.')
        return redirect(self.success_url)
    
class ZoneMapView(LoginRequiredMixin, TemplateView):
    template_name = 'access/zone_map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zones = AccessZone.objects.filter(is_active=True).select_related('institution')
        
        context['zones'] = zones
        context['active_zones'] = zones.filter(is_active=True).count()
        context['occupied_zones'] = zones.filter(current_occupancy__gt=0).count()
        
        
        return context


# def zone_map(request):
#     """Interactive zone map view"""
#     zones = AccessZone.objects.filter(is_active=True)
#     return render(request, 'access/zone_map.html', {'zones': zones})


# ============ Classroom Booking Views ============

class ClassroomBookingView(LoginRequiredMixin, TemplateView):
    """Classroom booking view"""
    template_name = 'access/classroom_booking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get available classrooms
        date = self.request.GET.get('date', timezone.now().date())
        context['classrooms'] = AccessZone.objects.filter(zone_type='classroom', is_active=True)
        context['selected_date'] = date
        
        # Get existing bookings for the date
        from apps.classroom.models import Class
        context['bookings'] = Class.objects.filter(
            start_date__lte=date,
            end_date__gte=date,
            is_active=True
        ).select_related('academic_unit', 'lecturer')
        
        return context


@csrf_exempt
def api_book_classroom(request):
    """API endpoint for classroom booking"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        zone_id = data.get('zone_id')
        date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        purpose = data.get('purpose')
        
        # Check if classroom is available
        zone = get_object_or_404(AccessZone, id=zone_id, zone_type='classroom')
        
        # Check for conflicts
        conflicting_bookings = Class.objects.filter(
            schedule__contains={'date': date},
            is_active=True
        )
        
        if conflicting_bookings.exists():
            return JsonResponse({
                'success': False,
                'error': 'Classroom already booked for this time slot'
            }, status=409)
        
        # Create booking (would need a Booking model)
        return JsonResponse({
            'success': True,
            'message': f'Classroom {zone.name} booked successfully',
            'booking_id': 1
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============ Permission Management Views ============

class PermissionListView(LoginRequiredMixin, ListView):
    """List access permissions"""
    model = AccessPermission
    ordering = ['-created_at']
    template_name = 'access/permission_list.html'
    context_object_name = 'permissions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AccessPermission.objects.filter(is_active=True).select_related('zone', 'specific_person')
        
        # Filter by zone
        zone_id = self.request.GET.get('zone_id')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        # Filter by person type
        person_type = self.request.GET.get('person_type')
        if person_type:
            queryset = queryset.filter(person_type=person_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zones'] = AccessZone.objects.filter(is_active=True)
        context['person_types'] = AccessPermission.PersonType.choices
        return context


class PermissionDetailView(LoginRequiredMixin, DetailView):
    """Permission detail view"""
    model = AccessPermission
    template_name = 'access/permission_detail.html'
    context_object_name = 'permission'


class PermissionCreateView(LoginRequiredMixin, CreateView):
    """Create new access permission"""
    model = AccessPermission
    # form = AccessPermissionModalForm
    fields = ['zone', 'person_type', 'college', 'school', 'department', 'specific_person',
              'valid_from', 'valid_to', 'monday', 'tuesday', 'wednesday', 'thursday',
              'friday', 'saturday', 'sunday', 'start_time', 'end_time', 'requires_2fa']
    template_name = 'access/permission_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Permission'
        context['zones'] = AccessZone.objects.filter(is_active=True)
        context['persons'] = Person.objects.filter(is_active=True)
        return context
    
    def get_success_url(self):
        return reverse_lazy('access:permission_list')


class PermissionUpdateView(LoginRequiredMixin, UpdateView):
    """Update access permission"""
    model = AccessPermission
    fields = ['zone', 'person_type', 'valid_from', 'valid_to', 'start_time', 'end_time', 'requires_2fa']
    template_name = 'access/permission_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Permission for {self.object.zone.name}'
        return context
    
    def get_success_url(self):
        return reverse_lazy('access:permission_detail', kwargs={'pk': self.object.pk})


class PermissionDeleteView(LoginRequiredMixin, DeleteView):
    """Delete access permission"""
    model = AccessPermission
    template_name = 'access/permission_confirm_delete.html'
    success_url = reverse_lazy('access:permission_list')


# ============ Access Log Views ============

class AccessLogListView(LoginRequiredMixin, ListView):
    """List access logs"""
    model = AccessLog
    ordering = ['-created_at']
    template_name = 'access/log_list.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AccessLog.objects.select_related('person', 'zone', 'node').order_by('-access_time')
        
        # Date range filters
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(access_time__date__gte=start_date)
        
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(access_time__date__lte=end_date)
        
        # Filter by result
        result = self.request.GET.get('result')
        if result:
            queryset = queryset.filter(result=result)
        
        # Filter by zone
        zone_id = self.request.GET.get('zone_id')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        # Filter by person
        person_id = self.request.GET.get('person_id')
        if person_id:
            queryset = queryset.filter(person_id=person_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zones'] = AccessZone.objects.filter(is_active=True)
        context['result_choices'] = AccessLog.AccessResult.choices
        context['total_count'] = self.get_queryset().count()
        context['granted_count'] = self.get_queryset().filter(result='granted').count()
        context['denied_count'] = self.get_queryset().filter(result='denied').count()
        return context


class AccessLogDetailView(LoginRequiredMixin, DetailView):
    """Access log detail view"""
    model = AccessLog
    template_name = 'access/log_detail.html'
    context_object_name = 'log'


@permission_required(VMSPermissions.ACCESS_VIEW_LOGS)
def export_access_logs(request):
    """Export access logs to CSV"""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="access_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Person', 'Zone', 'Method', 'Result', 'Reason', 'IP Address'])
    
    logs = AccessLog.objects.select_related('person', 'zone').order_by('-access_time')[:1000]
    for log in logs:
        writer.writerow([
            log.access_time.strftime('%Y-%m-%d %H:%M:%S'),
            log.person.full_name if log.person else 'Unknown',
            log.zone.name if log.zone else 'N/A',
            log.get_verification_method_display(),
            log.result,
            log.reason,
            log.ip_address or ''
        ])
    
    return response


@permission_required(VMSPermissions.ACCESS_VIEW_LOGS)
def clear_access_logs(request):
    """Clear old access logs"""
    if request.method == 'POST':
        days = int(request.POST.get('days', 30))
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days)
        deleted = AccessLog.objects.filter(access_time__lt=cutoff).delete()
        messages.success(request, f'Deleted {deleted[0]} logs older than {days} days.')
    return redirect('access:log_list')


# ============ 2FA Management Views ============

class TwoFactorSessionListView(LoginRequiredMixin, ListView):
    """List 2FA sessions"""
    model = TwoFactorSession
    ordering = ['-created_at']
    template_name = 'access/tfa_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        return TwoFactorSession.objects.select_related('person', 'zone').order_by('-created_at')


@csrf_exempt
def two_factor_verify(request):
    """Verify 2FA code"""
    if request.method == 'POST':
        data = json.loads(request.body)
        session_token = data.get('session_token')
        code = data.get('code')
        
        try:
            session = TwoFactorSession.objects.get(session_token=session_token)
            success, message = session.verify(code)
            
            if success:
                return JsonResponse({'success': True, 'message': message})
            else:
                return JsonResponse({'success': False, 'error': message}, status=400)
                
        except TwoFactorSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def two_factor_resend(request):
    """Resend 2FA code"""
    if request.method == 'POST':
        data = json.loads(request.body)
        session_token = data.get('session_token')
        
        try:
            session = TwoFactorSession.objects.get(session_token=session_token)
            # Resend OTP logic here
            return JsonResponse({'success': True})
        except TwoFactorSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============ Geofence Views ============

class GeofenceListView(LoginRequiredMixin, ListView):
    """List geofences"""
    model = GeofenceBoundary
    ordering = ['-created_at']
    template_name = 'access/geofence_list.html'
    context_object_name = 'geofences'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zones'] = AccessZone.objects.filter(is_active=True)
        context['total_geofences'] = GeofenceBoundary.objects.count()
        context['polygon_count'] = GeofenceBoundary.objects.filter(boundary_type='polygon').count()
        context['circle_count'] = GeofenceBoundary.objects.filter(boundary_type='circle').count()
        context['zones_protected'] = GeofenceBoundary.objects.values('zone').distinct().count()
        return context


class GeofenceDetailView(LoginRequiredMixin, DetailView):
    """Geofence detail view"""
    model = GeofenceBoundary
    template_name = 'access/geofence_detail.html'
    context_object_name = 'geofence'


class GeofenceCreateView(LoginRequiredMixin, CreateView):
    """Create new geofence"""
    model = GeofenceBoundary
    forms = GeofenceModalForm
    fields = ['zone', 'boundary_type', 'coordinates', 'latitude', 'longitude', 'radius_meters']
    template_name = 'access/geofence_form.html'
    
    def get_success_url(self):
        return reverse_lazy('access:geofence_detail', kwargs={'pk': self.object.pk})


class GeofenceUpdateView(LoginRequiredMixin, UpdateView):
    """Update geofence"""
    model = GeofenceBoundary
    fields = ['boundary_type', 'coordinates', 'latitude', 'longitude', 'radius_meters']
    template_name = 'access/geofence_form.html'
    
    def get_success_url(self):
        return reverse_lazy('access:geofence_detail', kwargs={'pk': self.object.pk})


# ============ Report Views ============

class AccessReportView(LoginRequiredMixin, TemplateView):
    """Access reports dashboard"""
    template_name = 'access/report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from datetime import timedelta
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        context['today_access'] = AccessLog.objects.filter(access_time__date=today).count()
        context['today_denied'] = AccessLog.objects.filter(access_time__date=today, result='denied').count()
        context['week_access'] = AccessLog.objects.filter(access_time__date__gte=week_ago).count()
        context['week_denied'] = AccessLog.objects.filter(access_time__date__gte=week_ago, result='denied').count()
        
        # Most accessed zones
        context['top_zones'] = list(AccessLog.objects.values('zone__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10])
        
        return context


def access_summary(request):
    """Access summary statistics (JSON)"""
    from datetime import timedelta
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    summary = {
        'today': {
            'total': AccessLog.objects.filter(access_time__date=today).count(),
            'granted': AccessLog.objects.filter(access_time__date=today, result='granted').count(),
            'denied': AccessLog.objects.filter(access_time__date=today, result='denied').count(),
        },
        'week': {
            'total': AccessLog.objects.filter(access_time__date__gte=week_ago).count(),
            'granted': AccessLog.objects.filter(access_time__date__gte=week_ago, result='granted').count(),
            'denied': AccessLog.objects.filter(access_time__date__gte=week_ago, result='denied').count(),
        },
        'by_hour': list(AccessLog.objects.filter(access_time__date=today).extra(
            {'hour': "strftime('%H', access_time)"}
        ).values('hour').annotate(count=Count('id')).order_by('hour'))
    }
    
    return JsonResponse(summary)


def access_failures(request):
    """Access failure report"""
    from datetime import timedelta
    failures = AccessLog.objects.filter(
        result='denied',
        access_time__date__gte=timezone.now().date() - timedelta(days=7)
    ).select_related('person', 'zone').order_by('-access_time')[:100]
    
    return render(request, 'access/failures.html', {'failures': failures})


# ============ API Endpoints ============

@csrf_exempt
def api_access_request(request):
    """API endpoint for access request from ESP32"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        credential = data.get('credential')
        zone_code = data.get('zone_code')
        node_uuid = data.get('node_uuid')
        
        service = AccessControlService()
        result = service.process_access_request(credential, zone_code, node_uuid)
        
        return JsonResponse(result, status=200 if result['granted'] else 403)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_verify_access(request):
    """Verify access via API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data = json.loads(request.body)
    person_id = data.get('person_id')
    zone_id = data.get('zone_id')
    
    service = AccessControlService()
    result = service.verify_access(person_id, zone_id)
    
    return JsonResponse(result)


@csrf_exempt
def api_override_access(request, pk):
    """Override access restriction"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    permission = get_object_or_404(AccessPermission, pk=pk)
    # Override logic here
    return JsonResponse({'success': True})


# ============ AJAX Endpoints ============

def ajax_check_access(request):
    """Check if person has access to zone"""
    person_id = request.GET.get('person_id')
    zone_id = request.GET.get('zone_id')
    
    service = AccessControlService()
    has_access = service.check_person_access(person_id, zone_id)
    
    return JsonResponse({'has_access': has_access})


def ajax_zone_occupancy(request):
    """Get current occupancy for zones"""
    zone_id = request.GET.get('zone_id')
    
    if zone_id:
        zone = get_object_or_404(AccessZone, pk=zone_id)
        return JsonResponse({
            'zone_id': zone.id,
            'zone_name': zone.name,
            'current': zone.current_occupancy,
            'capacity': zone.capacity,
            'percentage': round((zone.current_occupancy / zone.capacity * 100), 1) if zone.capacity > 0 else 0
        })
    else:
        zones = AccessZone.objects.filter(is_active=True)
        data = [{
            'id': z.id,
            'name': z.name,
            'current': z.current_occupancy,
            'capacity': z.capacity,
            'percentage': round((z.current_occupancy / z.capacity * 100), 1) if z.capacity > 0 else 0
        } for z in zones]
        return JsonResponse({'zones': data})


def ajax_current_logs(request):
    """Get current access logs for dashboard"""
    logs = AccessLog.objects.select_related('person', 'zone').order_by('-access_time')[:20]
    
    data = [{
        'time': log.access_time.strftime('%H:%M:%S'),
        'person': log.person.full_name if log.person else 'Unknown',
        'zone': log.zone.name if log.zone else 'N/A',
        'result': log.result,
        'method': log.get_verification_method_display()
    } for log in logs]
    
    return JsonResponse({'logs': data})


@csrf_exempt
def toggle_zone_status(request, pk):
    """Toggle zone active status"""
    if request.method == 'POST':
        try:
            zone = AccessZone.objects.get(pk=pk, is_active=True)
            zone.is_active = False
            zone.save()
            return JsonResponse({'success': True, 'is_active': False})
        except AccessZone.DoesNotExist:
            try:
                zone = AccessZone.objects.get(pk=pk, is_active=False)
                zone.is_active = True
                zone.save()
                return JsonResponse({'success': True, 'is_active': True})
            except AccessZone.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Zone not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def toggle_permission_status(request, pk):
    if request.method == 'POST':
        try:
            permission = AccessPermission.objects.get(pk=pk)
            permission.is_active = not permission.is_active
            permission.save()
            return JsonResponse({'success': True, 'is_active': permission.is_active})
        except AccessPermission.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Permission not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
def toggle_geofence_status(request, pk):
    if request.method == 'POST':
        try:
            geofence = GeofenceBoundary.objects.get(pk=pk)
            geofence.is_active = not geofence.is_active
            geofence.save()
            return JsonResponse({'success': True, 'is_active': geofence.is_active})
        except GeofenceBoundary.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Geofence not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
def export_geofence_geojson(request, pk):
    """Export single geofence as GeoJSON"""
    try:
        geofence = GeofenceBoundary.objects.select_related('zone').get(pk=pk)
        geojson = geofence.get_geojson()
        
        response = JsonResponse(geojson, safe=False)
        response['Content-Disposition'] = f'attachment; filename="geofence_{geofence.zone.name}_{pk}.geojson"'
        return response
    except GeofenceBoundary.DoesNotExist:
        return JsonResponse({'error': 'Geofence not found'}, status=404)

@csrf_exempt
def export_all_geojson(request):
    """Export all geofences as GeoJSON FeatureCollection"""
    geofences = GeofenceBoundary.objects.select_related('zone').filter(is_active=True)
    features = []
    
    for gf in geofences:
        geojson = gf.get_geojson()
        if geojson:
            features.append(geojson)
    
    collection = {
        "type": "FeatureCollection",
        "features": features
    }
    
    response = JsonResponse(collection, safe=False)
    response['Content-Disposition'] = 'attachment; filename="all_geofences.geojson"'
    return response

@csrf_exempt
def zone_detail_json(request, pk):
    zone = get_object_or_404(AccessZone.objects.select_related(
        'institution', 'college', 'school', 'department', 'zone'
    ), pk=pk)
    data = {
        'id': zone.id,
        'name': zone.name,
        'code': zone.code,
        'zone_type': zone.zone_type,
        'zone_type_display': zone.get_zone_type_display(),
        'building': zone.building,
        'room_number': zone.room_number,
        'capacity': zone.capacity,
        'current_occupancy': zone.current_occupancy,
        'access_level': zone.access_level,
        'is_active': zone.is_active,
        'requires_2fa': zone.requires_2fa,
        'description': zone.description,
        'parent_zone': zone.parent_zone.name if zone.parent_zone else None,
        'institution': zone.institution.name if zone.institution else None,
        'college': zone.college.name if zone.college else None,
        'school': zone.school.name if zone.school else None,
        'department': zone.department.name if zone.department else None,
    }
    return render(request, 'access/zone_detail_modal.html', {'zone': data})

def get_zone_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        zone = AccessZone.objects.get(pk=pk)
        institutions = Institution.objects.filter(is_active=True)
        
        # Get related data for cascading selects
        colleges = College.objects.filter(is_active=True, institution_id=zone.institution_id) if zone.institution_id else []
        schools = School.objects.filter(is_active=True, college_id=zone.college_id) if zone.college_id else []
        departments = Department.objects.filter(is_active=True, school_id=zone.school_id) if zone.school_id else []
        
        html = f'''
        <form id="editZoneForm" method="POST" action="/access/zones/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label required">Zone Name</label>
                    <input type="text" name="name" class="form-control" value="{zone.name}" required>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Zone Code</label>
                    <input type="text" name="code" class="form-control" value="{zone.code or ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label required">Zone Type</label>
                    <select name="zone_type" class="form-select" required>
                        <option value="">Select Type</option>
                        <option value="classroom" {'selected' if zone.zone_type == 'classroom' else ''}>Classroom</option>
                        <option value="lab" {'selected' if zone.zone_type == 'lab' else ''}>Laboratory</option>
                        <option value="office" {'selected' if zone.zone_type == 'office' else ''}>Office</option>
                        <option value="hallway" {'selected' if zone.zone_type == 'hallway' else ''}>Hallway</option>
                        <option value="external" {'selected' if zone.zone_type == 'external' else ''}>External</option>
                        <option value="other" {'selected' if zone.zone_type == 'other' else ''}>Other</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Parent Zone</label>
                    <select name="parent_zone" class="form-select">
                        <option value="">None</option>
        '''
        
        # Add parent zones
        parent_zones = AccessZone.objects.filter(is_active=True).exclude(id=zone.id)
        for pz in parent_zones:
            selected = 'selected' if zone.parent_zone_id == pz.id else ''
            html += f'<option value="{pz.id}" {selected}>{pz.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label required">Institution</label>
                    <select name="institution" class="form-select" id="editInstitutionSelect" required>
                        <option value="">Select Institution</option>
        '''
        
        for inst in institutions:
            selected = 'selected' if zone.institution_id == inst.id else ''
            html += f'<option value="{inst.id}" {selected}>{inst.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">College</label>
                    <select name="college" class="form-select" id="editCollegeSelect">
                        <option value="">Select College</option>
        '''
        
        for college in colleges:
            selected = 'selected' if zone.college_id == college.id else ''
            html += f'<option value="{college.id}" {selected}>{college.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">School</label>
                    <select name="school" class="form-select" id="editSchoolSelect">
                        <option value="">Select School</option>
        '''
        
        for school in schools:
            selected = 'selected' if zone.school_id == school.id else ''
            html += f'<option value="{school.id}" {selected}>{school.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Department</label>
                    <select name="department" class="form-select" id="editDepartmentSelect">
                        <option value="">Select Department</option>
        '''
        
        for dept in departments:
            selected = 'selected' if zone.department_id == dept.id else ''
            html += f'<option value="{dept.id}" {selected}>{dept.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Building</label>
                    <input type="text" name="building" class="form-control" value="{zone.building or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Floor</label>
                    <input type="text" name="floor" class="form-control" value="{zone.floor or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Room Number</label>
                    <input type="text" name="room_number" class="form-control" value="{zone.room_number or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Capacity</label>
                    <input type="number" name="capacity" class="form-control" value="{zone.capacity or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Access Level</label>
                    <select name="access_level" class="form-select">
                        <option value="unrestricted" {'selected' if zone.access_level == 'unrestricted' else ''}>Unrestricted</option>
                        <option value="restricted" {'selected' if zone.access_level == 'restricted' else ''}>Restricted</option>
                        <option value="authorized_only" {'selected' if zone.access_level == 'authorized_only' else ''}>Authorized Only</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <div class="form-check mt-4">
                        <input type="checkbox" name="requires_2fa" class="form-check-input" id="editRequires2fa" {'checked' if zone.requires_2fa else ''}>
                        <label class="form-check-label" for="editRequires2fa">Requires 2FA</label>
                    </div>
                </div>
                <div class="col-12">
                    <label class="form-label">Description</label>
                    <textarea name="description" class="form-control" rows="2">{zone.description or ''}</textarea>
                </div>
            </div>
            <div class="modal-footer mt-3">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Zone</button>
            </div>
        </form>
        
        <script>
            // Initialize Select2 for the edit form
            $('#editZoneForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editZoneModal')
            }});
            
            // Handle cascading selects for edit form
            $('#editInstitutionSelect').on('change', function() {{
                const institutionId = $(this).val();
                if (institutionId) {{
                    $.get(`/api/institutions/${{institutionId}}/colleges/`, function(data) {{
                        let options = '<option value="">Select College</option>';
                        data.forEach(college => {{
                            options += `<option value="${{college.id}}">${{college.name}}</option>`;
                        }});
                        $('#editCollegeSelect').html(options);
                    }});
                }} else {{
                    $('#editCollegeSelect').html('<option value="">Select College</option>');
                    $('#editSchoolSelect').html('<option value="">Select School</option>');
                    $('#editDepartmentSelect').html('<option value="">Select Department</option>');
                }}
            }});
            
            $('#editCollegeSelect').on('change', function() {{
                const collegeId = $(this).val();
                if (collegeId) {{
                    $.get(`/api/colleges/${{collegeId}}/schools/`, function(data) {{
                        let options = '<option value="">Select School</option>';
                        data.forEach(school => {{
                            options += `<option value="${{school.id}}">${{school.name}}</option>`;
                        }});
                        $('#editSchoolSelect').html(options);
                    }});
                }} else {{
                    $('#editSchoolSelect').html('<option value="">Select School</option>');
                    $('#editDepartmentSelect').html('<option value="">Select Department</option>');
                }}
            }});
            
            $('#editSchoolSelect').on('change', function() {{
                const schoolId = $(this).val();
                if (schoolId) {{
                    $.get(`/api/schools/${{schoolId}}/departments/`, function(data) {{
                        let options = '<option value="">Select Department</option>';
                        data.forEach(dept => {{
                            options += `<option value="${{dept.id}}">${{dept.name}}</option>`;
                        }});
                        $('#editDepartmentSelect').html(options);
                    }});
                }} else {{
                    $('#editDepartmentSelect').html('<option value="">Select Department</option>');
                }}
            }});
            
            // Handle form submission
            $('#editZoneForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editZoneModal').modal('hide');
                            toastr.success(response.message || 'Zone updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update zone');
                            submitBtn.prop('disabled', false).html('Update Zone');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update Zone');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)

@csrf_exempt
def update_zone(request, pk):
    """Update zone via AJAX"""
    if request.method == 'POST':
        try:
            zone = AccessZone.objects.get(pk=pk)
            zone.name = request.POST.get('name')
            zone.code = request.POST.get('code')
            zone.zone_type = request.POST.get('zone_type')
            zone.parent_zone_id = request.POST.get('parent_zone') or None
            zone.institution_id = request.POST.get('institution') or None
            zone.college_id = request.POST.get('college') or None
            zone.school_id = request.POST.get('school') or None
            zone.department_id = request.POST.get('department') or None
            zone.building = request.POST.get('building')
            zone.floor = request.POST.get('floor')
            zone.room_number = request.POST.get('room_number')
            zone.capacity = request.POST.get('capacity') or None
            zone.access_level = request.POST.get('access_level')
            zone.requires_2fa = request.POST.get('requires_2fa') == 'on'
            zone.description = request.POST.get('description')
            zone.save()
            
            return JsonResponse({'success': True, 'message': f'Zone {zone.name} updated successfully'})
        except AccessZone.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Zone not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_zone_detail(request, pk):


    """Return zone detail HTML for AJAX modal"""
    zone = get_object_or_404(AccessZone, pk=pk)
    
    # Calculate occupancy percentage
    occupancy_percent = 0
    if zone.capacity and zone.capacity > 0:
        occupancy_percent = round((zone.current_occupancy / zone.capacity) * 100, 2)
    
    # Determine occupancy class and text
    if occupancy_percent >= 85:
        occupancy_class = 'danger'
        occupancy_text = 'Full'
    elif occupancy_percent >= 60:
        occupancy_class = 'warning'
        occupancy_text = 'Busy'
    elif occupancy_percent >= 20:
        occupancy_class = 'info'
        occupancy_text = 'Moderate'
    else:
        occupancy_class = 'success'
        occupancy_text = 'Available'
    
    # Determine status class
    status_class = 'success' if zone.is_active else 'secondary'
    status_text = 'Active' if zone.is_active else 'Inactive'
    
    # Determine access level display
    if zone.access_level == 'unrestricted':
        access_badge = 'success'
        access_display = 'Unrestricted Access'
    elif zone.access_level == 'restricted':
        access_badge = 'warning'
        access_display = 'Restricted Access'
    else:
        access_badge = 'danger'
        access_display = 'Authorized Only'
    
    html = f'''
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">Zone Name</div>
            <div class="detail-value"><strong>{zone.name}</strong></div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">Status</div>
            <div class="detail-value"><span class="badge bg-{status_class}">{status_text}</span></div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">Zone Code</div>
            <div class="detail-value">{zone.code or '—'}</div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">Zone Type</div>
            <div class="detail-value">
                <span class="zone-badge {zone.zone_type}">
                    {zone.get_zone_type_display()}
                </span>
            </div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">Parent Zone</div>
            <div class="detail-value">{zone.parent_zone.name if zone.parent_zone else '—'}</div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">Access Level</div>
            <div class="detail-value">
                <span class="badge bg-{access_badge}">{access_display}</span>
            </div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">Institution</div>
            <div class="detail-value">{zone.institution.name if zone.institution else '—'}</div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">College</div>
            <div class="detail-value">{zone.college.name if zone.college else '—'}</div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">School</div>
            <div class="detail-value">{zone.school.name if zone.school else '—'}</div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">Department</div>
            <div class="detail-value">{zone.department.name if zone.department else '—'}</div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-4">
            <div class="detail-label">Building</div>
            <div class="detail-value">{zone.building or '—'}</div>
        </div>
        <div class="col-md-4">
            <div class="detail-label">Floor</div>
            <div class="detail-value">{zone.floor or '—'}</div>
        </div>
        <div class="col-md-4">
            <div class="detail-label">Room Number</div>
            <div class="detail-value">{zone.room_number or '—'}</div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">Capacity</div>
            <div class="detail-value">{zone.capacity if zone.capacity else 'Unlimited'}</div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">Current Occupancy</div>
            <div class="detail-value">
                <div class="d-flex justify-content-between small mb-1">
                    <span>{zone.current_occupancy} / {zone.capacity if zone.capacity else '∞'}</span>
                    <span class="text-{occupancy_class}">{occupancy_percent}%</span>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar bg-{occupancy_class}" style="width: {occupancy_percent}%"></div>
                </div>
                <small class="text-muted mt-1 d-block">{occupancy_text}</small>
            </div>
        </div>
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="detail-label">2FA Required</div>
            <div class="detail-value">
                {'<span class="badge bg-warning">Yes</span>' if zone.requires_2fa else '<span class="badge bg-secondary">No</span>'}
            </div>
        </div>
        <div class="col-md-6">
            <div class="detail-label">Created</div>
            <div class="detail-value"></div>
        </div>
    </div>
    '''
    
    if zone.description:
        html += f'''
        <div class="row mb-3">
            <div class="col-12">
                <div class="detail-label">Description</div>
                <div class="detail-value">{zone.description}</div>
            </div>
        </div>
        '''
    
    return JsonResponse({'html': html, 'success': True})

def get_permission_detail(request, pk):
    """Return permission detail HTML for AJAX modal"""
    try:
        permission = AccessPermission.objects.select_related(
            'zone', 'college', 'school', 'department', 'program', 'specific_person'
        ).get(pk=pk)
        
        # Get days schedule
        days = []
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in day_names:
            if getattr(permission, day, False):
                days.append(day.capitalize())
        
        days_display = ', '.join(days) if days else 'All Days'
        
        # Time schedule
        time_display = "24/7"
        if permission.start_time and permission.end_time:
            time_display = f"{permission.start_time.strftime('%I:%M %p')} - {permission.end_time.strftime('%I:%M %p')}"
        
        # Valid period
        valid_period = "Always"
        if permission.valid_from and permission.valid_to:
            valid_period = f"{permission.valid_from.strftime('%Y-%m-%d %H:%M')} to {permission.valid_to.strftime('%Y-%m-%d %H:%M')}"
        elif permission.valid_from:
            valid_period = f"From {permission.valid_from.strftime('%Y-%m-%d %H:%M')}"
        elif permission.valid_to:
            valid_period = f"Until {permission.valid_to.strftime('%Y-%m-%d %H:%M')}"
        
        # Get person name
        person_name = "All Persons"
        if permission.specific_person:
            person_name = permission.specific_person.get_full_name() or permission.specific_person.username
        
        html = f'''
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Zone</div>
                <div class="detail-value">
                    <strong>{permission.zone.name}</strong>
                    <br><small class="text-muted">{permission.zone.get_zone_type_display()}</small>
                </div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Person Type</div>
                <div class="detail-value">
                    <span class="badge bg-primary">{permission.get_person_type_display()}</span>
                </div>
            </div>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Specific Person</div>
                <div class="detail-value">{person_name}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Priority</div>
                <div class="detail-value">
                    <span class="badge bg-secondary">Level {permission.priority}</span>
                </div>
            </div>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Valid Period</div>
                <div class="detail-value">{valid_period}</div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Schedule</div>
                <div class="detail-value">
                    <div><strong>Days:</strong> {days_display}</div>
                    <div><strong>Time:</strong> {time_display}</div>
                </div>
            </div>
        </div>
        '''
        
        # Add academic filters if applicable
        filters = []
        if permission.college:
            filters.append(f"College: {permission.college.name}")
        if permission.school:
            filters.append(f"School: {permission.school.name}")
        if permission.department:
            filters.append(f"Department: {permission.department.name}")
        if permission.program:
            filters.append(f"Program: {permission.program.name}")
        if permission.year_of_study:
            filters.append(f"Year of Study: {permission.year_of_study}")
        if permission.staff_category:
            filters.append(f"Staff Category: {permission.staff_category}")
        
        if filters:
            html += f'''
            <div class="row mb-3">
                <div class="col-12">
                    <div class="detail-label">Additional Filters</div>
                    <div class="detail-value">
                        <ul class="mb-0">
                            {''.join([f'<li>{f}</li>' for f in filters])}
                        </ul>
                    </div>
                </div>
            </div>
            '''
        
        html += f'''
        <div class="row mb-3">
            <div class="col-md-4">
                <div class="detail-label">Requirements</div>
                <div class="detail-value">
                    {'<span class="badge bg-warning me-1">2FA Required</span>' if permission.requires_2fa else ''}
                    {'<span class="badge bg-info me-1">Escort Required</span>' if permission.requires_escort else ''}
                    {'<span class="badge bg-danger me-1">Approval Required</span>' if permission.requires_approval else ''}
                    {'' if permission.requires_2fa or permission.requires_escort or permission.requires_approval else '<span class="text-muted">None</span>'}
                </div>
            </div>
        </div>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)

def get_permission_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        permission = AccessPermission.objects.get(pk=pk)
        zones = AccessZone.objects.filter(is_active=True)
        colleges = College.objects.filter(is_active=True)
        schools = School.objects.filter(is_active=True)
        departments = Department.objects.filter(is_active=True)
        programs = Program.objects.filter(is_active=True)
        persons = Person.objects.filter(is_active=True)
        
        # Format datetime values
        valid_from = permission.valid_from.strftime('%Y-%m-%dT%H:%M') if permission.valid_from else ''
        valid_to = permission.valid_to.strftime('%Y-%m-%dT%H:%M') if permission.valid_to else ''
        start_time = permission.start_time.strftime('%H:%M') if permission.start_time else ''
        end_time = permission.end_time.strftime('%H:%M') if permission.end_time else ''
        
        html = f'''
        <form id="editPermissionForm" method="POST" action="/access/permissions/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label required">Zone</label>
                    <select name="zone" class="form-select" required>
                        <option value="">Select Zone</option>
        '''
        
        for zone in zones:
            selected = 'selected' if permission.zone_id == zone.id else ''
            html += f'<option value="{zone.id}" {selected}>{zone.name} ({zone.get_zone_type_display()})</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Person Type</label>
                    <select name="person_type" class="form-select">
                        <option value="">All Types</option>
        '''
        
        for value, label in AccessPermission.PersonType.choices:
            selected = 'selected' if permission.person_type == value else ''
            html += f'<option value="{value}" {selected}>{label}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">College</label>
                    <select name="college" class="form-select">
                        <option value="">All Colleges</option>
        '''
        
        for college in colleges:
            selected = 'selected' if permission.college_id == college.id else ''
            html += f'<option value="{college.id}" {selected}>{college.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">School</label>
                    <select name="school" class="form-select">
                        <option value="">All Schools</option>
        '''
        
        for school in schools:
            selected = 'selected' if permission.school_id == school.id else ''
            html += f'<option value="{school.id}" {selected}>{school.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Department</label>
                    <select name="department" class="form-select">
                        <option value="">All Departments</option>
        '''
        
        for dept in departments:
            selected = 'selected' if permission.department_id == dept.id else ''
            html += f'<option value="{dept.id}" {selected}>{dept.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Program</label>
                    <select name="program" class="form-select">
                        <option value="">All Programs</option>
        '''
        
        for prog in programs:
            selected = 'selected' if permission.program_id == prog.id else ''
            html += f'<option value="{prog.id}" {selected}>{prog.name}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Year of Study</label>
                    <input type="number" name="year_of_study" class="form-control" min="1" max="6" value="{permission.year_of_study or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Staff Category</label>
                    <input type="text" name="staff_category" class="form-control" value="{permission.staff_category or ''}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">Specific Person</label>
                    <select name="specific_person" class="form-select">
                        <option value="">None</option>
        '''
        
        for person in persons:
            selected = 'selected' if permission.specific_person_id == person.id else ''
            html += f'<option value="{person.id}" {selected}>{person.get_full_name()} - {person.email}</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Valid From</label>
                    <input type="datetime-local" name="valid_from" class="form-control" value="{valid_from}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Valid To</label>
                    <input type="datetime-local" name="valid_to" class="form-control" value="{valid_to}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Start Time</label>
                    <input type="time" name="start_time" class="form-control" value="{start_time}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">End Time</label>
                    <input type="time" name="end_time" class="form-control" value="{end_time}">
                </div>
                <div class="col-12">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="monday" class="form-check-input" id="editMonday" {'checked' if permission.monday else ''}>
                                <label class="form-check-label" for="editMonday">Monday</label>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="tuesday" class="form-check-input" id="editTuesday" {'checked' if permission.tuesday else ''}>
                                <label class="form-check-label" for="editTuesday">Tuesday</label>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="wednesday" class="form-check-input" id="editWednesday" {'checked' if permission.wednesday else ''}>
                                <label class="form-check-label" for="editWednesday">Wednesday</label>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="thursday" class="form-check-input" id="editThursday" {'checked' if permission.thursday else ''}>
                                <label class="form-check-label" for="editThursday">Thursday</label>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="friday" class="form-check-input" id="editFriday" {'checked' if permission.friday else ''}>
                                <label class="form-check-label" for="editFriday">Friday</label>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="saturday" class="form-check-input" id="editSaturday" {'checked' if permission.saturday else ''}>
                                <label class="form-check-label" for="editSaturday">Saturday</label>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-check">
                                <input type="checkbox" name="sunday" class="form-check-input" id="editSunday" {'checked' if permission.sunday else ''}>
                                <label class="form-check-label" for="editSunday">Sunday</label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check mt-2">
                        <input type="checkbox" name="requires_2fa" class="form-check-input" id="editRequires2fa" {'checked' if permission.requires_2fa else ''}>
                        <label class="form-check-label" for="editRequires2fa">Requires 2FA</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check mt-2">
                        <input type="checkbox" name="requires_escort" class="form-check-input" id="editRequiresEscort" {'checked' if permission.requires_escort else ''}>
                        <label class="form-check-label" for="editRequiresEscort">Requires Escort</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check mt-2">
                        <input type="checkbox" name="requires_approval" class="form-check-input" id="editRequiresApproval" {'checked' if permission.requires_approval else ''}>
                        <label class="form-check-label" for="editRequiresApproval">Requires Approval</label>
                    </div>
                </div>
                <div class="col-md-12">
                    <label class="form-label">Priority</label>
                    <input type="number" name="priority" class="form-control" min="0" value="{permission.priority}">
                </div>
            </div>
            <div class="modal-footer mt-3">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Permission</button>
            </div>
        </form>
        
        <script>
            // Initialize Select2 for the edit form
            $('#editPermissionForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editPermissionModal')
            }});
            
            // Handle form submission
            $('#editPermissionForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editPermissionModal').modal('hide');
                            toastr.success(response.message || 'Permission updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update permission');
                            submitBtn.prop('disabled', false).html('Update Permission');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update Permission');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)

@csrf_exempt
def update_permission(request, pk):
    """Update permission via AJAX"""
    if request.method == 'POST':
        try:
            permission = AccessPermission.objects.get(pk=pk)
            
            # Basic fields
            permission.zone_id = request.POST.get('zone')
            permission.person_type = request.POST.get('person_type') or 'all'
            permission.college_id = request.POST.get('college') or None
            permission.school_id = request.POST.get('school') or None
            permission.department_id = request.POST.get('department') or None
            permission.program_id = request.POST.get('program') or None
            permission.year_of_study = request.POST.get('year_of_study') or None
            permission.staff_category = request.POST.get('staff_category') or None
            permission.specific_person_id = request.POST.get('specific_person') or None
            
            # Date/time fields
            permission.valid_from = request.POST.get('valid_from') or None
            permission.valid_to = request.POST.get('valid_to') or None
            permission.start_time = request.POST.get('start_time') or None
            permission.end_time = request.POST.get('end_time') or None
            
            # Day checkboxes
            permission.monday = request.POST.get('monday') == 'on'
            permission.tuesday = request.POST.get('tuesday') == 'on'
            permission.wednesday = request.POST.get('wednesday') == 'on'
            permission.thursday = request.POST.get('thursday') == 'on'
            permission.friday = request.POST.get('friday') == 'on'
            permission.saturday = request.POST.get('saturday') == 'on'
            permission.sunday = request.POST.get('sunday') == 'on'
            
            # Requirements
            permission.requires_2fa = request.POST.get('requires_2fa') == 'on'
            permission.requires_escort = request.POST.get('requires_escort') == 'on'
            permission.requires_approval = request.POST.get('requires_approval') == 'on'
            permission.priority = request.POST.get('priority') or 0
            
            permission.save()
            
            return JsonResponse({'success': True, 'message': f'Permission updated successfully'})
        except AccessPermission.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Permission not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def create_permission(request):
    """Create permission via AJAX"""
    if request.method == 'POST':
        try:
            permission = AccessPermission()
            
            # Basic fields
            permission.zone_id = request.POST.get('zone')
            permission.person_type = request.POST.get('person_type') or 'all'
            permission.college_id = request.POST.get('college') or None
            permission.school_id = request.POST.get('school') or None
            permission.department_id = request.POST.get('department') or None
            permission.program_id = request.POST.get('program') or None
            permission.year_of_study = request.POST.get('year_of_study') or None
            permission.staff_category = request.POST.get('staff_category') or None
            permission.specific_person_id = request.POST.get('specific_person') or None
            
            # Date/time fields
            permission.valid_from = request.POST.get('valid_from') or None
            permission.valid_to = request.POST.get('valid_to') or None
            permission.start_time = request.POST.get('start_time') or None
            permission.end_time = request.POST.get('end_time') or None
            
            # Day checkboxes (default to all true if not set)
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            any_day_selected = any(request.POST.get(day) == 'on' for day in days)

            permission.monday = request.POST.get('monday') == 'on' or not any_day_selected
            permission.tuesday = request.POST.get('tuesday') == 'on' or not any_day_selected
            permission.wednesday = request.POST.get('wednesday') == 'on' or not any_day_selected
            permission.thursday = request.POST.get('thursday') == 'on' or not any_day_selected
            permission.friday = request.POST.get('friday') == 'on' or not any_day_selected
            permission.saturday = request.POST.get('saturday') == 'on' or not any_day_selected
            permission.sunday = request.POST.get('sunday') == 'on' or not any_day_selected
            
            # Requirements
            permission.requires_2fa = request.POST.get('requires_2fa') == 'on'
            permission.requires_escort = request.POST.get('requires_escort') == 'on'
            permission.requires_approval = request.POST.get('requires_approval') == 'on'
            permission.priority = request.POST.get('priority') or 0
            
            permission.save()
            
            return JsonResponse({'success': True, 'message': f'Permission created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def toggle_permission_status(request, pk):
    """Toggle permission active status via AJAX"""
    if request.method == 'POST':
        try:
            permission = AccessPermission.objects.get(pk=pk)
            permission.is_active = not permission.is_active
            permission.save()
            status_text = 'activated' if permission.is_active else 'deactivated'
            return JsonResponse({'success': True, 'message': f'Permission {status_text} successfully'})
        except AccessPermission.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Permission not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_geofence_detail(request, pk):
    """Return geofence detail HTML for AJAX modal"""
    try:
        geofence = GeofenceBoundary.objects.select_related('zone').get(pk=pk)
        
        # Format coordinates for display
        coords_display = "—"
        if geofence.boundary_type == 'polygon' and geofence.coordinates:
            try:
                coords = json.loads(geofence.coordinates) if isinstance(geofence.coordinates, str) else geofence.coordinates
                coords_display = f"{len(coords)} points"
            except:
                coords_display = str(geofence.coordinates)[:100]
        elif geofence.boundary_type == 'circle':
            coords_display = f"Center: {geofence.latitude}, {geofence.longitude} | Radius: {geofence.radius_meters}m"
        elif geofence.boundary_type == 'point':
            coords_display = f"{geofence.latitude}, {geofence.longitude}"
        
        html = f'''
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Zone</div>
                <div class="detail-value">
                    <strong>{geofence.zone.name}</strong>
                    <br><small class="text-muted">{geofence.zone.get_zone_type_display()}</small>
                </div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Boundary Type</div>
                <div class="detail-value">
                    <span class="badge bg-primary">{geofence.get_boundary_type_display()}</span>
                </div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Coordinates</div>
                <div class="detail-value">
                    <code class="small">{coords_display}</code>
                </div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Accuracy Threshold</div>
                <div class="detail-value">
                    {geofence.accuracy_threshold} meters
                </div>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="detail-label">Status</div>
                <div class="detail-value">
                    {"<span class='badge bg-success'>Active</span>" if geofence.is_active else "<span class='badge bg-secondary'>Inactive</span>"}
                </div>
            </div>
            <div class="col-md-6">
                <div class="detail-label">Created</div>
                <div class="detail-value">
                    {geofence.created_at.strftime('%Y-%m-%d %H:%M') if geofence.created_at else '—'}
                </div>
            </div>
        </div>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)
    
def get_geofence_edit_form(request, pk):
    """Return edit form HTML for AJAX modal"""
    try:
        geofence = GeofenceBoundary.objects.get(pk=pk)
        zones = AccessZone.objects.filter(is_active=True)
        
        # Prepare values
        coordinates = ""
        if geofence.coordinates:
            if isinstance(geofence.coordinates, dict):
                coordinates = json.dumps(geofence.coordinates)
            elif isinstance(geofence.coordinates, list):
                coordinates = json.dumps(geofence.coordinates)
            else:
                coordinates = str(geofence.coordinates)
        
        html = f'''
        <form id="editGeofenceForm" method="POST" action="/access/geofences/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label required">Zone</label>
                    <select name="zone" class="form-select" required>
                        <option value="">Select Zone</option>
        '''
        
        for zone in zones:
            selected = 'selected' if geofence.zone_id == zone.id else ''
            html += f'<option value="{zone.id}" {selected}>{zone.name} ({zone.get_zone_type_display()})</option>'
        
        html += f'''
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label required">Boundary Type</label>
                    <select name="boundary_type" class="form-select" id="editBoundaryTypeSelect" required>
                        <option value="polygon" {'selected' if geofence.boundary_type == 'polygon' else ''}>Polygon (Area)</option>
                        <option value="circle" {'selected' if geofence.boundary_type == 'circle' else ''}>Circle (Radius)</option>
                        <option value="point" {'selected' if geofence.boundary_type == 'point' else ''}>Point (Single Location)</option>
                        <option value="path" {'selected' if geofence.boundary_type == 'path' else ''}>Path/Route</option>
                    </select>
                </div>
                
                <div class="col-12" id="editPolygonFields" {'style="display: none;"' if geofence.boundary_type != 'polygon' else ''}>
                    <label class="form-label">Polygon Coordinates</label>
                    <textarea name="coordinates" class="form-control coordinate-input" rows="4" placeholder="[[lat,lng], [lat,lng], ...]">{coordinates}</textarea>
                    <small class="text-muted">Enter coordinates as JSON array of [lat, lng] pairs</small>
                </div>
                
                <div class="row" id="editCircleFields" {'style="display: none;"' if geofence.boundary_type != 'circle' else ''}>
                    <div class="col-md-4">
                        <label class="form-label">Latitude</label>
                        <input type="number" step="any" name="latitude" class="form-control" value="{geofence.latitude or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Longitude</label>
                        <input type="number" step="any" name="longitude" class="form-control" value="{geofence.longitude or ''}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Radius (meters)</label>
                        <input type="number" name="radius_meters" class="form-control" value="{geofence.radius_meters or ''}">
                    </div>
                </div>
                
                <div class="col-md-6">
                    <label class="form-label">Accuracy Threshold (meters)</label>
                    <input type="number" name="accuracy_threshold" class="form-control" value="{geofence.accuracy_threshold}">
                    <small class="text-muted">GPS accuracy required for geofence validation</small>
                </div>
                <div class="col-md-6">
                    <div class="form-check mt-4">
                        <input type="checkbox" name="is_active" class="form-check-input" id="editIsActive" {'checked' if geofence.is_active else ''}>
                        <label class="form-check-label" for="editIsActive">Active</label>
                    </div>
                </div>
            </div>
            <div class="modal-footer mt-3">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Geofence</button>
            </div>
        </form>
        
        <script>
            // Toggle fields based on boundary type
            $('#editBoundaryTypeSelect').on('change', function() {{
                const type = $(this).val();
                $('#editPolygonFields, #editCircleFields').hide();
                if (type === 'polygon') $('#editPolygonFields').show();
                else if (type === 'circle') $('#editCircleFields').show();
            }});
            
            // Initialize Select2
            $('#editGeofenceForm .form-select').select2({{
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#editGeofenceModal')
            }});
            
            // Handle form submission
            $('#editGeofenceForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                
                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                
                $.ajax({{
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editGeofenceModal').modal('hide');
                            toastr.success(response.message || 'Geofence updated successfully!');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{
                            toastr.error(response.error || 'Failed to update geofence');
                            submitBtn.prop('disabled', false).html('Update Geofence');
                        }}
                    }},
                    error: function(xhr) {{
                        let errorMsg = 'An error occurred';
                        if (xhr.responseJSON && xhr.responseJSON.error) {{
                            errorMsg = xhr.responseJSON.error;
                        }}
                        toastr.error(errorMsg);
                        submitBtn.prop('disabled', false).html('Update Geofence');
                    }}
                }});
            }});
        </script>
        '''
        
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)

@csrf_exempt
def create_geofence(request):
    """Create geofence via AJAX"""
    if request.method == 'POST':
        try:
            geofence = GeofenceBoundary()
            geofence.zone_id = request.POST.get('zone')
            geofence.boundary_type = request.POST.get('boundary_type')
            geofence.accuracy_threshold = request.POST.get('accuracy_threshold') or 10
            geofence.is_active = request.POST.get('is_active') == 'on'
            
            # Handle based on boundary type
            if geofence.boundary_type == 'polygon':
                coordinates = request.POST.get('coordinates')
                if coordinates:
                    import json
                    geofence.coordinates = json.loads(coordinates)
            elif geofence.boundary_type == 'circle':
                geofence.latitude = request.POST.get('latitude')
                geofence.longitude = request.POST.get('longitude')
                geofence.radius_meters = request.POST.get('radius_meters')
                geofence.coordinates = [float(geofence.latitude), float(geofence.longitude)]
            elif geofence.boundary_type == 'point':
                geofence.latitude = request.POST.get('latitude')
                geofence.longitude = request.POST.get('longitude')
                geofence.coordinates = [float(geofence.latitude), float(geofence.longitude)]
            
            geofence.save()
            
            return JsonResponse({'success': True, 'message': f'Geofence created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def update_geofence(request, pk):
    """Update geofence via AJAX"""
    if request.method == 'POST':
        try:
            geofence = GeofenceBoundary.objects.get(pk=pk)
            geofence.zone_id = request.POST.get('zone')
            geofence.boundary_type = request.POST.get('boundary_type')
            geofence.accuracy_threshold = request.POST.get('accuracy_threshold') or 10
            geofence.is_active = request.POST.get('is_active') == 'on'
            
            # Handle based on boundary type
            if geofence.boundary_type == 'polygon':
                coordinates = request.POST.get('coordinates')
                if coordinates:
                    import json
                    geofence.coordinates = json.loads(coordinates)
            elif geofence.boundary_type == 'circle':
                geofence.latitude = request.POST.get('latitude')
                geofence.longitude = request.POST.get('longitude')
                geofence.radius_meters = request.POST.get('radius_meters')
                geofence.coordinates = [float(geofence.latitude), float(geofence.longitude)]
            elif geofence.boundary_type == 'point':
                geofence.latitude = request.POST.get('latitude')
                geofence.longitude = request.POST.get('longitude')
                geofence.coordinates = [float(geofence.latitude), float(geofence.longitude)]
            
            geofence.save()
            
            return JsonResponse({'success': True, 'message': f'Geofence updated successfully'})
        except GeofenceBoundary.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Geofence not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def toggle_geofence_status(request, pk):
    """Toggle geofence active status via AJAX"""
    if request.method == 'POST':
        try:
            geofence = GeofenceBoundary.objects.get(pk=pk)
            geofence.is_active = not geofence.is_active
            geofence.save()
            status_text = 'activated' if geofence.is_active else 'deactivated'
            return JsonResponse({'success': True, 'message': f'Geofence {status_text} successfully'})
        except GeofenceBoundary.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Geofence not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def export_geofence_geojson(request, pk):
    """Export geofence as GeoJSON"""
    try:
        geofence = GeofenceBoundary.objects.select_related('zone').get(pk=pk)
        geojson = geofence.get_geojson()
        return JsonResponse(geojson, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)