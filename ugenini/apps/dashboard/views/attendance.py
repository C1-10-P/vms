# apps/dashboard/views/attendance.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .base import DashboardBaseView
from apps.classroom.services import AttendanceService
from apps.classroom.models import ClassAttendance
from apps.core.models import Student, Class


class AttendanceDashboardView(DashboardBaseView):
    """Attendance module dashboard"""
    template_name = 'dashboard/attendance/index.html'
    module_name = 'attendance'
    section_name = 'dashboard'
    page_title = 'Attendance Dashboard'
    page_description = 'Monitor and manage attendance records'
    permission_required = 'attendance.view_classattendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        week_ago = today - timezone.timedelta(days=7)
        
        # Statistics
        context['today_attendance'] = ClassAttendance.objects.filter(
            scan_time__date=today,
            verification_status='success'
        ).count()
        
        context['week_attendance'] = ClassAttendance.objects.filter(
            scan_time__date__gte=week_ago,
            verification_status='success'
        ).count()
        
        context['total_students'] = Student.objects.filter(is_active=True).count()
        context['active_classes'] = Class.objects.filter(is_active=True).count()
        
        # Recent attendance
        context['recent_attendances'] = ClassAttendance.objects.select_related(
            'student__person', 'class_obj'
        ).order_by('-scan_time')[:20]
        
        return context


class AttendanceCheckInView(DashboardBaseView):
    """Take attendance view"""
    template_name = 'dashboard/attendance/check_in.html'
    module_name = 'attendance'
    section_name = 'check_in'
    page_title = 'Take Attendance'
    page_description = 'Scan or manually record attendance'
    permission_required = 'attendance.add_classattendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = Class.objects.filter(is_active=True)
        return context
    
    def post(self, request):
        student_reg = request.POST.get('student_reg')
        class_code = request.POST.get('class_code')
        scan_method = request.POST.get('scan_method', 'manual')
        
        if not student_reg or not class_code:
            messages.error(request, 'Please provide student registration and class code')
            return redirect('dashboard:attendance_checkin')
        
        service = AttendanceService()
        result = service.process_api_check_in(student_reg, class_code, scan_method)
        
        if result.get('success'):
            messages.success(request, f"Attendance recorded for {result.get('student_name')}")
        else:
            messages.error(request, result.get('error', 'Failed to record attendance'))
        
        return redirect('dashboard:attendance_checkin')


class AttendanceListView(DashboardBaseView):
    """Attendance records list"""
    template_name = 'dashboard/attendance/list.html'
    module_name = 'attendance'
    section_name = 'list'
    page_title = 'Attendance Records'
    page_description = 'View and manage attendance records'
    permission_required = 'attendance.view_classattendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        class_id = self.request.GET.get('class_id')
        student_id = self.request.GET.get('student_id')
        
        queryset = ClassAttendance.objects.select_related(
            'student__person', 'class_obj'
        )
        
        if start_date:
            queryset = queryset.filter(scan_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scan_time__date__lte=end_date)
        if class_id:
            queryset = queryset.filter(class_obj_id=class_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        context['attendances'] = queryset.order_by('-scan_time')[:100]
        context['classes'] = Class.objects.filter(is_active=True)
        context['students'] = Student.objects.select_related('person').filter(is_active=True)[:50]
        
        # Preserve filter values
        context['filters'] = {
            'start_date': start_date,
            'end_date': end_date,
            'class_id': class_id,
            'student_id': student_id,
        }
        
        return context


class AttendanceReportsView(DashboardBaseView):
    """Attendance reports"""
    template_name = 'dashboard/attendance/reports.html'
    module_name = 'attendance'
    section_name = 'reports'
    page_title = 'Attendance Reports'
    page_description = 'Generate and download attendance reports'
    permission_required = 'attendance.view_classattendance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from datetime import timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Daily trend
        daily_trend = ClassAttendance.objects.filter(
            scan_time__date__gte=start_date,
            verification_status='success'
        ).annotate(date=TruncDate('scan_time')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        context['daily_trend'] = list(daily_trend)
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        return context