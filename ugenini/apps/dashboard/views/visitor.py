# apps/dashboard/views/visitors.py
from datetime import timezone

from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

from apps.access.models.zone import AccessZone

from .base import DashboardBaseView
from apps.vms.services import VisitorService
from apps.vms.models import Visitor, VisitorVisit


class VisitorDashboardView(DashboardBaseView):
    """Visitor module dashboard"""
    template_name = 'dashboard/visitors/index.html'
    module_name = 'visitors'
    section_name = 'dashboard'
    page_title = 'Visitor Dashboard'
    page_description = 'Manage and track visitors'
    permission_required = 'visitors.view_visitor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        
        context['active_visitors'] = VisitorVisit.objects.filter(status='active').count()
        context['today_checkins'] = VisitorVisit.objects.filter(
            check_in_time__date=today
        ).count()
        context['total_visitors_today'] = VisitorVisit.objects.filter(
            check_in_time__date=today
        ).values('visitor').distinct().count()
        
        context['recent_visitors'] = VisitorVisit.objects.select_related(
            'visitor__person'
        ).order_by('-check_in_time')[:20]
        
        return context


class VisitorCheckInView(DashboardBaseView):
    """Visitor check-in view"""
    template_name = 'dashboard/visitors/checkin.html'
    module_name = 'visitors'
    section_name = 'checkin'
    page_title = 'Visitor Check-in'
    page_description = 'Register new visitor'
    permission_required = 'visitors.add_visitor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.vms.models import BLETag
        context['available_tags'] = BLETag.objects.filter(status='available')
        return context
    
    def post(self, request):
        visitor_data = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'phone_number': request.POST.get('phone_number'),
            'national_id': request.POST.get('national_id'),
            'email': request.POST.get('email', ''),
            'organization': request.POST.get('organization', ''),
            'purpose': request.POST.get('purpose', 'meeting'),
        }
        
        service = VisitorService()
        result = service.process_visitor_checkin(visitor_data)
        
        if result.get('success'):
            messages.success(request, f"Visitor checked in: {result.get('visitor_name', 'Success')}")
            
            # Assign tag if provided
            tag_id = request.POST.get('tag_id')
            if tag_id:
                from apps.vms.models import BLETag
                tag = BLETag.objects.filter(id=tag_id).first()
                if tag:
                    tag.assign_to_visitor(
                        Visitor.objects.get(id=result['visitor_id']),
                        request.user.person.staff if hasattr(request.user, 'person') else None
                    )
                    messages.info(request, f"Tag {tag.tag_uuid} assigned to visitor")
        else:
            messages.error(request, result.get('error', 'Check-in failed'))
        
        return redirect('dashboard:visitors_checkin')


class VisitorTrackingView(DashboardBaseView):
    """Visitor tracking view"""
    template_name = 'dashboard/visitors/tracking.html'
    module_name = 'visitors'
    section_name = 'tracking'
    page_title = 'Live Tracking'
    page_description = 'Real-time visitor tracking'
    permission_required = 'visitors.view_visitor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from apps.vms.movement_service import VisitorMovementService
        
        context['active_visitors'] = VisitorMovementService.get_active_visitor_locations()
        context['zones'] = AccessZone.objects.filter(is_active=True)
        
        return context


class VisitorMapView(DashboardBaseView):
    """Visitor map view with OpenStreetMap"""
    template_name = 'dashboard/visitors/map.html'
    module_name = 'visitors'
    section_name = 'map'
    page_title = 'Visitor Map'
    page_description = 'Geographic visitor tracking'
    permission_required = 'visitors.view_visitor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from apps.vms.movement_service import VisitorMovementService
        from apps.access.models import AccessZone
        
        context['active_visitors'] = VisitorMovementService.get_active_visitor_locations()
        context['zones'] = AccessZone.objects.filter(is_active=True)
        
        # Map configuration
        context['map_center'] = [-1.2921, 36.8219]  # Default center
        context['map_zoom'] = 15
        
        return context