# apps/dashboard/views/base.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect


class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """
    Base class for all dashboard views
    Handles common functionality like breadcrumbs, page titles, and permissions
    """
    
    # Module configuration
    module_name = None           # 'attendance', 'visitors', etc.
    section_name = None          # 'dashboard', 'checkin', etc.
    page_title = 'Dashboard'
    page_description = ''
    breadcrumbs = []
    
    # Permission required (override in child classes)
    permission_required = None
    
    def dispatch(self, request, *args, **kwargs):
        # Check permission if specified
        if self.permission_required:
            if not request.user.has_perm(self.permission_required):
                messages.error(request, f'You don\'t have permission to access this page.')
                return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Set page metadata
        context['module_name'] = self.module_name
        context['section_name'] = self.section_name
        context['page_title'] = self.page_title
        context['page_description'] = self.page_description
        context['breadcrumbs'] = self.get_breadcrumbs()
        
        # Add user permissions for sidebar highlighting
        context['user_permissions'] = self.get_user_permissions()
        
        return context
    
    def get_breadcrumbs(self):
        """Build breadcrumb navigation"""
        breadcrumbs = [{'title': 'Dashboard', 'url': reverse('dashboard:home')}]
        
        if self.module_name:
            module_url = reverse(f'dashboard:{self.module_name}')
            breadcrumbs.append({
                'title': self.module_name.title(),
                'url': module_url
            })
        
        if self.section_name and self.section_name != 'dashboard':
            breadcrumbs.append({
                'title': self.section_name.title().replace('_', ' '),
                'url': None
            })
        
        return breadcrumbs
    
    def get_user_permissions(self):
        """Get user permissions for sidebar highlighting"""
        user = self.request.user
        return {
            'can_view_attendance': user.has_perm('attendance.view_classattendance'),
            'can_view_visitors': user.has_perm('visitors.view_visitor'),
            'can_view_access': user.has_perm('access.view_accesszone'),
            'can_view_devices': user.has_perm('devices.view_edgenode'),
            'can_view_reports': user.has_perm('reports.view_report'),
            'is_admin': user.is_staff or user.is_superuser,
        }


class DashboardHomeView(DashboardBaseView):
    """Main dashboard landing page"""
    template_name = 'dashboard/index.html'
    page_title = 'Overview'
    page_description = 'Welcome to VMS Dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add dashboard statistics
        from apps.dashboard.services import DashboardDataService
        service = DashboardDataService()
        
        context['stats'] = service.get_dashboard_stats(self.request.user)
        context['recent_activity'] = service.get_recent_activity()
        context['attendance_chart_data'] = service.get_attendance_chart_data()
        context['visitor_chart_data'] = service.get_visitor_chart_data()
        
        return context