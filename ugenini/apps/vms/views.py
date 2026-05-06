from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import Visitor, BLETag, VisitorVisit, VisitorMovement, VisitorAlert, BlacklistedVisitor
from .services import VisitorService
from apps.core.models import Person, Staff
from apps.access.models.zone import AccessZone
from .movement_service import VisitorMovementService

# ============ Visitor CRUD Views ============

class VisitorListView(LoginRequiredMixin, ListView):
    """List all visitors"""
    model = Visitor
    ordering = ['-created_at']
    template_name = 'vms/visitor_list.html'
    context_object_name = 'visitors'
    paginate_by = 20
    
    def get_queryset(self):
        # 1. Subquery using 'status' instead of 'is_active'
        active_blacklist_subquery = BlacklistedVisitor.objects.filter(
            visitor=OuterRef('pk'),
            status='active'
        )

        # 2. RENAME the annotation to avoid collision with the model property
        queryset = Visitor.objects.filter(is_active=True).select_related(
            'person', 'current_visit'
        ).annotate(
            is_on_blacklist=Exists(active_blacklist_subquery)
        )
    
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(person__first_name__icontains=search) |
                Q(person__last_name__icontains=search) |
                Q(id_number__icontains=search) |
                Q(organization__icontains=search)
            )
    
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(current_visit__isnull=False)
        elif status_filter == 'blacklisted':
            # Use the new annotated name here too
            queryset = queryset.filter(is_on_blacklist=True)
        elif status_filter == 'inactive':
            # Use the new annotated name here too
            queryset = queryset.filter(current_visit__isnull=True, is_on_blacklist=False)
        
        return queryset.order_by('person__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_visitors'] = Visitor.objects.count()
        context['active_visitors'] = VisitorVisit.objects.filter(status='active').count()
        
        # 2. Corrected count using status='active'
        active_blacklist_subquery = BlacklistedVisitor.objects.filter(
            visitor=OuterRef('pk'),
            status='active'
        )
        context['blacklisted_count'] = Visitor.objects.annotate(
            is_blacklisted=Exists(active_blacklist_subquery)
        ).filter(is_blacklisted=True).count()
        
        return context

class VisitorDetailView(LoginRequiredMixin, DetailView):
    """Visitor detail view"""
    model = Visitor
    template_name = 'vms/visitor_detail.html'
    context_object_name = 'visitor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get visit history
        context['visits'] = self.object.visits.all().order_by('-check_in_time')[:20]
        
        # Get current visit
        context['current_visit'] = self.object.current_visit
        
        # Get movement history
        context['movements'] = VisitorMovement.objects.filter(
            visitor=self.object
        ).select_related('zone').order_by('-timestamp')[:50]
        
        # Get alerts
        context['alerts'] = VisitorAlert.objects.filter(
            visitor=self.object
        ).order_by('-triggered_at')[:20]
        
        # Check if visitor is on campus
        context['is_on_campus'] = self.object.is_on_campus()
        
        return context


class VisitorCreateView(LoginRequiredMixin, CreateView):
    """Create new visitor"""
    model = Visitor
    fields = ['purpose', 'purpose_description', 'host_person', 'organization', 'vehicle_registration']
    template_name = 'vms/visitor_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Visitor'
        context['staff_members'] = Staff.objects.select_related('person').filter(is_active=True)
        return context
    
    def form_valid(self, form):
        # Create person first
        person = Person.objects.create(
            first_name=self.request.POST.get('first_name'),
            last_name=self.request.POST.get('last_name'),
            email=self.request.POST.get('email', ''),
            phone_number=self.request.POST.get('phone_number'),
            national_id=self.request.POST.get('national_id'),
            person_type='visitor'
        )
        
        form.instance.person = person
        form.instance.id_number = self.request.POST.get('national_id')
        form.instance.id_type = 'national_id'
        
        response = super().form_valid(form)
        messages.success(self.request, f'Visitor {person.full_name} created successfully.')
        return response
    
    def get_success_url(self):
        return reverse_lazy('vms:detail', kwargs={'pk': self.object.pk})


class VisitorUpdateView(LoginRequiredMixin, UpdateView):
    """Update visitor information"""
    model = Visitor
    fields = ['purpose', 'purpose_description', 'host_person', 'organization', 'vehicle_registration']
    template_name = 'vms/visitor_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Visitor: {self.object.person.full_name}'
        context['staff_members'] = Staff.objects.select_related('person').filter(is_active=True)
        return context
    
    def get_success_url(self):
        return reverse_lazy('vms:detail', kwargs={'pk': self.object.pk})


class VisitorDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete visitor"""
    model = Visitor
    template_name = 'vms/visitor_confirm_delete.html'
    success_url = reverse_lazy('vms:list')
    
    def delete(self, request, *args, **kwargs):
        visitor = self.get_object()
        visitor.soft_delete()
        messages.success(request, f'Visitor {visitor.person.full_name} has been archived.')
        return redirect(self.success_url)


# ============ Visitor Check-in/out Views ============

class VisitorCheckInView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Visitor check-in view - handles new visitor registration and check-in
    """
    model = VisitorVisit
    fields = []
    template_name = 'vms/checkin.html'

    permission_required = VMSPermissions.VISITOR_CHECKOUT
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        # Ensure self.object exists to avoid CreateView errors
        if not hasattr(self, 'object'):
            self.object = None
        context = super().get_context_data(**kwargs)
        context['available_tags'] = BLETag.objects.filter(status='available')
        context['staff_members'] = Staff.objects.select_related('person').filter(is_active=True)
        return context

    def post(self, request, *args, **kwargs):
        self.object = None

        # Prepare visitor data from POST
        visitor_data = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'phone_number': request.POST.get('phone_number', '').strip(),
            'national_id': request.POST.get('national_id', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'organization': request.POST.get('organization', '').strip(),
            'purpose': request.POST.get('purpose', 'meeting'),
            'purpose_description': request.POST.get('purpose_description', ''),
            'host_email': request.POST.get('host_email', '').strip(),
        }

        # Get the staff user performing the check-in (for audit trail)
        staff_member = None
        if hasattr(request.user, 'person') and hasattr(request.user.person, 'staff'):
            staff_member = request.user.person.staff
        elif request.user.is_superuser:
            # Fallback: take the first active staff member for superuser (avoid NOT NULL constraint)
            staff_member = Staff.objects.filter(is_active=True).first()

        # Call the service
        service = VisitorService()
        result = service.process_visitor_checkin(data=visitor_data, staff_user=staff_member)

        if result['success']:
            visitor_id = result['visitor_id']
            # Assign BLE tag if selected
            tag_id = request.POST.get('tag_id')
            if tag_id:
                try:
                    tag = BLETag.objects.get(id=tag_id)
                    tag.assign_to_visitor(
                        Visitor.objects.get(id=visitor_id),
                        staff_member
                    )
                    messages.success(request, f"Tag {tag.tag_uuid} assigned to visitor.")
                except BLETag.DoesNotExist:
                    messages.warning(request, "Selected tag not found.")
                except Exception as e:
                    messages.error(request, f"Tag assignment failed: {str(e)}")

            messages.success(request, f"Visitor checked in successfully. ID: {result.get('visitor_id')}")
            return redirect('visitors:detail', pk=visitor_id)
        else:
            # Failure: show error and re-render form
            messages.error(request, result.get('error', 'Check-in failed. Please check the information and try again.'))
            return self.render_to_response(self.get_context_data())


class VisitorCheckOutView(LoginRequiredMixin,PermissionRequiredMixin, UpdateView):
    """
    Visitor check-out view - ends an active visit and releases BLE tag
    """
    model = VisitorVisit
    fields = []
    template_name = 'vms/checkout.html'

    permission_required = VMSPermissions.VISITOR_CHECKOUT
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_object(self):
        return get_object_or_404(VisitorVisit, id=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        visit = self.get_object()
        # Ensure the visit is still active
        if visit.status != 'active':
            messages.warning(request, f"This visit is already {visit.status}.")
            return redirect('visitors:detail', pk=visit.visitor.id)

        # Perform check-out
        visit.check_out_time = timezone.now()
        visit.status = 'completed'

        # Assign staff who performed check-out
        staff_member = None
        if hasattr(request.user, 'person') and hasattr(request.user.person, 'staff'):
            staff_member = request.user.person.staff
        elif request.user.is_superuser:
            staff_member = Staff.objects.filter(is_active=True).first()
        visit.checked_out_by = staff_member
        visit.save()

        # Release assigned BLE tag if any
        if visit.assigned_tag:
            try:
                visit.assigned_tag.release(staff_member)
                messages.info(request, f"Tag {visit.assigned_tag.tag_uuid} released.")
            except Exception as e:
                messages.error(request, f"Error releasing tag: {str(e)}")

        messages.success(request, f'Visitor {visit.visitor.person.full_name} checked out successfully.')
        return redirect('visitors:detail', pk=visit.visitor.id)

# ============ Visitor Tracking Views ============

class VisitorTrackingView(LoginRequiredMixin, TemplateView):
    """Real-time visitor tracking view"""
    template_name = 'vms/tracking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active visitors with their last known locations
        active_visits = VisitorVisit.objects.filter(status='active').select_related('visitor__person', 'assigned_tag')
        
        active_visitors = []
        for visit in active_visits:
            last_movement = VisitorMovement.objects.filter(
                visitor=visit.visitor
            ).order_by('-timestamp').first()
            
            active_visitors.append({
                'id': visit.visitor.id,
                'name': visit.visitor.person.full_name,
                'check_in_time': visit.check_in_time,
                'tag_id': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
                'last_location': last_movement.zone.name if last_movement and last_movement.zone else 'Unknown',
                'last_seen': last_movement.timestamp if last_movement else visit.check_in_time
            })
        
        context['active_visitors'] = active_visitors
        context['zones'] = AccessZone.objects.filter(is_active=True)
        
        return context


def visitor_tracking_map(request):
    """Visitor tracking map view"""
    return render(request, 'vms/tracking_map.html')


def visitor_movement_history(request, pk):
    """Visitor movement history view"""
    visitor = get_object_or_404(Visitor, pk=pk)
    movements = VisitorMovement.objects.filter(visitor=visitor).select_related('zone').order_by('-timestamp')[:100]
    return render(request, 'vms/movement_history.html', {'visitor': visitor, 'movements': movements})


def visitor_live_tracking(request):
    """Live visitor tracking view with WebSocket"""
    return render(request, 'vms/live_tracking.html')


# ============ BLE Tag Management Views ============

class BLETagListView(LoginRequiredMixin, ListView):
    """List BLE tags"""
    model = BLETag
    ordering = ['-created_at']
    template_name = 'vms/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(tag_uuid__icontains=search) |
                Q(hardware_id__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_tags'] = BLETag.objects.count()
        context['available_tags'] = BLETag.objects.filter(status='available').count()
        context['assigned_tags'] = BLETag.objects.filter(status='assigned').count()
        return context


class BLETagDetailView(LoginRequiredMixin, DetailView):
    """BLE tag detail view"""
    model = BLETag
    template_name = 'vms/tag_detail.html'
    context_object_name = 'tag'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment_history'] = self.object.assignments.all().order_by('-assigned_at')[:20]
        context['movement_history'] = VisitorMovement.objects.filter(tag=self.object).order_by('-timestamp')[:50]
        return context


class BLETagCreateView(LoginRequiredMixin, CreateView):
    """Create new BLE tag"""
    model = BLETag
    fields = ['tag_uuid', 'hardware_id', 'tag_type', 'manufacturer', 'model']
    template_name = 'vms/tag_form.html'
    success_url = reverse_lazy('vms:tag_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'BLE Tag {form.instance.tag_uuid} created successfully.')
        return super().form_valid(form)


class BLETagUpdateView(LoginRequiredMixin, UpdateView):
    """Update BLE tag"""
    model = BLETag
    fields = ['status', 'battery_level', 'firmware_version']
    template_name = 'vms/tag_form.html'
    
    def get_success_url(self):
        return reverse_lazy('vms:tag_detail', kwargs={'pk': self.object.pk})


class BLETagAssignView(LoginRequiredMixin, UpdateView):
    """Assign BLE tag to visitor"""
    model = BLETag
    fields = []
    template_name = 'vms/tag_assign.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['visitors'] = Visitor.objects.filter(is_active=True, current_visit__isnull=False)
        return context
    
    def post(self, request, *args, **kwargs):
        tag = self.get_object()
        visitor_id = request.POST.get('visitor_id')
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        # Safely try to get the staff object
        staff_profile = None
        if hasattr(request.user, 'person'):
            staff_profile = getattr(request.user.person, 'staff', None)

        if staff_profile is None:
            messages.error(request, "Error: Your user account is not associated with a Staff profile. Assignment failed.")
            return redirect('vms:tag_list') # Redirect to a safe page

        # If we got here, staff_profile is valid
        try:
            tag.assign_to_visitor(visitor, staff_profile)
            messages.success(request, f'Tag assigned successfully.')
        except Exception as e:
            messages.error(request, f"System error: {str(e)}")
            
        return redirect('vms:tag_detail', pk=tag.id)


class BLETagReleaseView(LoginRequiredMixin, UpdateView):
    """Release BLE tag from visitor"""
    model = BLETag
    fields = []
    template_name = 'vms/tag_release.html'
    
    def post(self, request, *args, **kwargs):
        tag = self.get_object()
        tag.release(request.user.person.staff if hasattr(request.user, 'person') else None)
        messages.success(request, f'Tag {tag.tag_uuid} released successfully.')
        return redirect('vms:tag_detail', pk=tag.id)


class BLETagMaintenanceView(LoginRequiredMixin, UpdateView):
    """Mark tag for maintenance"""
    model = BLETag
    fields = ['status']
    template_name = 'vms/tag_maintenance.html'
    
    def post(self, request, *args, **kwargs):
        tag = self.get_object()
        tag.status = 'maintenance'
        tag.save()
        messages.success(request, f'Tag {tag.tag_uuid} marked for maintenance.')
        return redirect('vms:tag_detail', pk=tag.id)


# ============ Visitor Alert Views ============

class VisitorAlertListView(LoginRequiredMixin, ListView):
    """List visitor alerts"""
    model = VisitorAlert
    ordering = ['-created_at']
    template_name = 'vms/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = VisitorAlert.objects.select_related('visitor__person', 'zone').order_by('-triggered_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by severity
        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['new_count'] = VisitorAlert.objects.filter(status='new').count()
        return context


@csrf_exempt
def acknowledge_alert(request, pk):
    """Acknowledge a visitor alert"""
    if request.method == 'POST':
        alert = get_object_or_404(VisitorAlert, pk=pk)
        alert.acknowledge(request.user.person.staff if hasattr(request.user, 'person') else None)
        return JsonResponse({'status': 'acknowledged'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def resolve_alert(request, pk):
    """Resolve a visitor alert"""
    if request.method == 'POST':
        alert = get_object_or_404(VisitorAlert, pk=pk)
        notes = request.POST.get('notes', '')
        alert.resolve(request.user.person.staff if hasattr(request.user, 'person') else None, notes)
        return JsonResponse({'status': 'resolved'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============ Report Views ============

class VisitorReportView(LoginRequiredMixin, TemplateView):
    """Visitor reports view"""
    template_name = 'vms/report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from datetime import timedelta
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        visits = VisitorVisit.objects.filter(
            check_in_time__date__gte=start_date,
            check_in_time__date__lte=end_date
        )
        
        context['total_visits'] = visits.count()
        context['unique_visitors'] = visits.values('visitor').distinct().count()
        context['daily_average'] = round(visits.count() / 30, 1)
        
        # Most common purposes
        context['purposes'] = list(Visitor.objects.values('purpose').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
        
        return context


def daily_visitor_report(request):
    """Daily visitor report"""
    date = request.GET.get('date', timezone.now().date())
    visits = VisitorVisit.objects.filter(check_in_time__date=date)
    
    context = {
        'date': date,
        'visits': visits,
        'total': visits.count()
    }
    return render(request, 'vms/daily_report.html', context)


def weekly_visitor_report(request):
    """Weekly visitor report"""
    from datetime import timedelta
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    from django.db.models.functions import TruncDate
    from django.db.models import Count
    
    stats = VisitorVisit.objects.filter(
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date
    ).annotate(date=TruncDate('check_in_time')).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    return render(request, 'vms/weekly_report.html', {'stats': stats, 'start_date': start_date, 'end_date': end_date})


def monthly_visitor_report(request):
    """Monthly visitor report"""
    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    
    visits = VisitorVisit.objects.filter(
        check_in_time__year=year,
        check_in_time__month=month
    )
    
    return render(request, 'vms/monthly_report.html', {
        'month': month,
        'year': year,
        'total': visits.count()
    })


# ============ Export Views ============

@permission_required(VMSPermissions.VISITOR_VIEW)
def export_visitors_csv(request):
    """Export visitors to CSV"""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="visitors.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'ID Number', 'Phone', 'Organization', 'Purpose', 'Last Visit', 'Total Visits'])
    
    visitors = Visitor.objects.select_related('person').filter(is_active=True)
    for visitor in visitors:
        writer.writerow([
            visitor.person.full_name,
            visitor.id_number,
            visitor.person.phone_number,
            visitor.organization,
            visitor.get_purpose_display(),
            visitor.last_visit.strftime('%Y-%m-%d') if visitor.last_visit else '',
            visitor.total_visits
        ])
    
    return response


@permission_required(VMSPermissions.VISITOR_VIEW)
def export_visitors_excel(request):
    """Export visitors to Excel"""
    from openpyxl import Workbook
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Visitors"
    
    headers = ['Name', 'ID Number', 'Phone', 'Email', 'Organization', 'Purpose', 'Last Visit', 'Total Visits']
    ws.append(headers)
    
    visitors = Visitor.objects.select_related('person').filter(is_active=True)
    for visitor in visitors:
        ws.append([
            visitor.person.full_name,
            visitor.id_number,
            visitor.person.phone_number,
            visitor.person.email,
            visitor.organization,
            visitor.get_purpose_display(),
            visitor.last_visit.strftime('%Y-%m-%d') if visitor.last_visit else '',
            visitor.total_visits
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="visitors.xlsx"'
    wb.save(response)
    return response


# ============ API Endpoints for ESP32 ============

@csrf_exempt
def api_visitor_checkin(request):
    """API endpoint for visitor check-in from kiosk"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        visitor_data = {
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'phone_number': data.get('phone_number'),
            'national_id': data.get('national_id'),
            'email': data.get('email', ''),
            'organization': data.get('organization', ''),
            'purpose': data.get('purpose', 'meeting'),
            'host_email': data.get('host_email', '')
        }
        
        service = VisitorService()
        result = service.process_visitor_checkin(visitor_data)
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_visitor_checkout(request, tag_uuid):
    """API endpoint for visitor check-out"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        tag = get_object_or_404(BLETag, tag_uuid=tag_uuid)
        
        service = VisitorService()
        result = service.process_visitor_checkout(tag)
        
        if result['success']:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_visitor_tracking(request, tag_uuid):
    """API endpoint for visitor tracking (ESP32 location updates)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        zone_code = data.get('zone_code')
        rssi = data.get('rssi')
        
        service = VisitorService()
        result = service.track_visitor_movement(tag_uuid, zone_code, None, rssi)
        
        return JsonResponse(result, status=200 if result['success'] else 404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_update_location(request):
    """API endpoint for location updates from ESP32"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        tag_uuid = data.get('tag_uuid')
        zone_code = data.get('zone_code')
        node_uuid = data.get('node_uuid')
        
        service = VisitorService()
        result = service.track_visitor_movement(tag_uuid, zone_code, node_uuid, data.get('rssi'))
        
        return JsonResponse(result, status=200 if result['success'] else 404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============ AJAX Endpoints ============

def ajax_search_visitors(request):
    """AJAX endpoint for visitor search"""
    query = request.GET.get('q', '')
    visitors = Visitor.objects.filter(
        Q(person__first_name__icontains=query) |
        Q(person__last_name__icontains=query) |
        Q(id_number__icontains=query),
        is_active=True
    ).select_related('person')[:10]
    
    results = [{
        'id': v.id,
        'name': v.person.full_name,
        'id_number': v.id_number,
        'is_active': v.is_on_campus()
    } for v in visitors]
    
    return JsonResponse({'results': results})


def ajax_active_visitors_count(request):
    """Get active visitors count"""
    count = VisitorVisit.objects.filter(status='active').count()
    return JsonResponse({'count': count})


def ajax_tag_status(request, tag_uuid):
    """Get tag status"""
    try:
        tag = BLETag.objects.get(tag_uuid=tag_uuid)
        return JsonResponse({
            'status': tag.status,
            'battery': tag.battery_level,
            'assigned_to': tag.current_visitor.person.full_name if tag.current_visitor else None
        })
    except BLETag.DoesNotExist:
        return JsonResponse({'error': 'Tag not found'}, status=404)
    

def get_tag_edit_form(request, pk):
    try:
        tag = BLETag.objects.get(pk=pk)
        html = f'''
        <form id="editTagForm" method="POST" action="/vms/tags/{pk}/update/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-12">
                        <label class="form-label">Status</label>
                        <select name="status" class="form-select">
                            <option value="available" {'selected' if tag.status == 'available' else ''}>Available</option>
                            <option value="assigned" {'selected' if tag.status == 'assigned' else ''}>Assigned</option>
                            <option value="maintenance" {'selected' if tag.status == 'maintenance' else ''}>Maintenance</option>
                            <option value="deprecated" {'selected' if tag.status == 'deprecated' else ''}>Deprecated</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Battery Level (%)</label>
                        <input type="number" name="battery_level" class="form-control" min="0" max="100" value="{tag.battery_level or 100}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Firmware Version</label>
                        <input type="text" name="firmware_version" class="form-control" value="{tag.firmware_version or ''}">
                    </div>
                    <div class="col-6">
                        <div class="form-check mt-4">
                            <input type="checkbox" name="is_active" class="form-check-input" {'checked' if tag.is_active else ''}>
                            <label class="form-check-label">Active</label>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Tag</button>
            </div>
        </form>
        <script>
            $('#editTagForm').on('submit', function(e) {{
                e.preventDefault();
                const form = $(this), btn = form.find('button[type="submit"]');
                btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Updating...');
                $.ajax({{
                    url: form.attr('action'), method: 'POST', data: form.serialize(),
                    success: function(response) {{
                        if (response.success) {{
                            $('#editTagModal').modal('hide');
                            toastr.success('Tag updated successfully');
                            setTimeout(() => location.reload(), 1500);
                        }} else {{ toastr.error(response.error || 'Failed to update'); btn.prop('disabled', false).html('Update Tag'); }}
                    }}, error: function() {{ toastr.error('An error occurred'); btn.prop('disabled', false).html('Update Tag'); }}
                }});
            }});
            $('#editTagForm .form-select').select2({{theme: 'bootstrap-5', width: '100%', dropdownParent: $('#editTagModal')}});
        </script>
        '''
        return JsonResponse({'html': html, 'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


@csrf_exempt
def update_tag(request, pk):
    if request.method == 'POST':
        try:
            tag = BLETag.objects.get(pk=pk)
            tag.status = request.POST.get('status')
            tag.battery_level = request.POST.get('battery_level')
            tag.firmware_version = request.POST.get('firmware_version')
            tag.is_active = request.POST.get('is_active') == 'on'
            tag.save()
            return JsonResponse({'success': True, 'message': f'Tag {tag.tag_uuid} updated successfully'})
        except BLETag.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Tag not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

def refresh_tracking_data(request):
    """API endpoint to refresh tracking data"""
    active_visits = VisitorVisit.objects.filter(status='active').select_related('visitor__person', 'assigned_tag')
    
    visitors = []
    for visit in active_visits:
        last_movement = VisitorMovement.objects.filter(
            visitor=visit.visitor
        ).order_by('-timestamp').first()
        
        visitors.append({
            'id': visit.visitor.id,
            'name': visit.visitor.person.get_full_name(),
            'tag_id': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
            'check_in_time': visit.check_in_time.strftime("%H:%i"),
            'last_location': last_movement.zone.name if last_movement and last_movement.zone else 'Unknown',
            'last_seen': last_movement.timestamp.strftime("%H:%i:%s") if last_movement else visit.check_in_time.strftime("%H:%i:%s")
        })
    
    return JsonResponse({'success': True, 'visitors': visitors})

# 

def visitor_movement_history(request, pk):
    """Return movement history as JSON for modal"""

    visitor = get_object_or_404(Visitor, pk=pk)
    movements = VisitorMovement.objects.filter(
        visitor=visitor
    ).select_related('zone').order_by('-timestamp')[:50]
    
    data = {
        'movements': []
    }
    
    for movement in movements:
        # Calculate distance using the service method
        distance = VisitorMovementService.calculate_distance_from_rssi(movement.rssi) if movement.rssi else -1.0
        
        data['movements'].append({
            'zone': movement.zone.name if movement.zone else 'Unknown',
            'timestamp': movement.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'rssi': movement.rssi,
            'event_type': movement.event_type,
            'distance': round(distance, 2) if distance > 0 else '—',
            'latitude': float(movement.latitude) if movement.latitude else None,
            'longitude': float(movement.longitude) if movement.longitude else None,
            'accuracy': float(movement.accuracy) if movement.accuracy else None
        })
    
    return JsonResponse(data)


def refresh_tracking_data(request):
    """API endpoint to refresh tracking data"""
    from .models import VisitorVisit, VisitorMovement
    
    active_visits = VisitorVisit.objects.filter(
        status='active'
    ).select_related('visitor__person', 'assigned_tag')
    
    visitors = []
    for visit in active_visits:
        last_movement = VisitorMovement.objects.filter(
            visitor=visit.visitor
        ).order_by('-timestamp').first()
        
        # Calculate distance for display
        distance = "—"
        if last_movement and last_movement.rssi:
            dist = VisitorMovementService.calculate_distance_from_rssi(last_movement.rssi)
            if dist > 0:
                distance = f"{round(dist, 1)}m"
        
        visitors.append({
            'id': visit.visitor.id,
            'name': visit.visitor.person.get_full_name(),
            'tag_id': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
            'check_in_time': visit.check_in_time.strftime("%H:%M"),
            'last_location': last_movement.zone.name if last_movement and last_movement.zone else 'Unknown',
            'last_seen': last_movement.timestamp.strftime("%H:%M:%S") if last_movement else visit.check_in_time.strftime("%H:%M:%S"),
            'distance': distance,
            'rssi': last_movement.rssi if last_movement else None
        })
    
    return JsonResponse({'success': True, 'visitors': visitors})