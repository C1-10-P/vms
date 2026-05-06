from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, DetailView, UpdateView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q
import json
import uuid

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import AttendanceSession, ClassAttendance
from .forms import AttendanceSessionForm, AttendanceSessionValidateForm
from .services import AttendanceSessionService
from apps.core.models import Student, Class


class AttendanceSessionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    View for creating a new attendance session
    Supports both manual entry and QR/OCR scanning
    """
    model = AttendanceSession
    form_class = AttendanceSessionForm
    template_name = 'classroom/session_create.html'
    
    # Use the Mixin attribute instead of the decorator
    permission_required = VMSPermissions.ATTENDANCE_CREATE
    
    # (Removed the @permission_required decorator from dispatch)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Attendance Session'
        context['students'] = Student.objects.select_related('person').filter(is_active=True)[:50]
        context['classes'] = Class.objects.filter(is_active=True)
        context['scan_methods'] = AttendanceSession.ScanMethod.choices
        return context
    
    def form_valid(self, form):
        """Process valid form submission"""
        session = form.save(commit=False)
        session.session_id = str(uuid.uuid4())
        # Use a more robust way to get IP if behind a proxy
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
            
        session.scan_device = ip
        session.ip_address = ip
        session.user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        session.save()
        
        messages.success(self.request, f'Attendance session created. Session ID: {session.session_id[:8]}')
        
        if session.student_reg_number and session.class_code:
            return redirect('classroom:session_validate', session_id=session.session_id)
        
        return redirect('classroom:session_detail', pk=session.pk)
    
    def get_success_url(self):
        return reverse_lazy('classroom:session_list')


class AttendanceSessionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View session details and validation status
    """
    model = AttendanceSession
    template_name = 'classroom/session_detail.html'
    context_object_name = 'session'
    
    # Standard CBV way to check permissions
    permission_required = VMSPermissions.ATTENDANCE_VIEW
    
    # No need for the @permission_required decorator here anymore!
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get validation form
        context['validate_form'] = AttendanceSessionValidateForm()
        
        # Get related attendance if exists
        if self.object.attendance:
            context['attendance'] = self.object.attendance
        
        # Calculate time remaining
        if self.object.is_valid():
            remaining = (self.object.expires_at - timezone.now()).total_seconds()
            context['seconds_remaining'] = int(remaining)
            context['minutes_remaining'] = int(remaining // 60)
        else:
            context['seconds_remaining'] = 0
            context['minutes_remaining'] = 0
        
        return context


class AttendanceSessionValidateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for validating an attendance session
    """
    model = AttendanceSession
    form_class = AttendanceSessionValidateForm
    template_name = 'classroom/session_validate.html'
    context_object_name = 'session'
    
    # Standard CBV way to handle permissions
    permission_required = VMSPermissions.ATTENDANCE_VERIFY
    
    # Removed the @permission_required decorator here
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_object(self):
        # Using session_id from URL kwargs instead of PK
        return get_object_or_404(AttendanceSession, session_id=self.kwargs.get('session_id'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Validate Attendance Session'
        context['session_id'] = self.object.session_id
        return context
    
    def form_valid(self, form):
        """Process validation"""
        session = self.object
        
        # Increment attempt counter
        session.increment_attempt()
        
        # Validate the session using your service layer
        result = AttendanceSessionService.validate_session(session.session_id)
        
        if result['success']:
            messages.success(self.request, f"Attendance recorded successfully for {result.get('student_name', 'student')}")
            return redirect('classroom:session_detail', pk=session.pk)
        else:
            messages.error(self.request, result.get('error', 'Validation failed'))
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('classroom:session_list', kwargs={'pk': self.object.pk})


class AttendanceSessionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List all attendance sessions
    """
    model = AttendanceSession
    ordering = ['-created_at']
    template_name = 'classroom/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    # Correct way to handle permissions in a Class-Based View
    permission_required = VMSPermissions.ATTENDANCE_VIEW
    
    # Dispatch is now handled safely by the Mixin
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        # 1. FIX: Chain 'student__person' to fetch the name data in one go
        queryset = AttendanceSession.objects.select_related(
            'student__person', 
            'class_obj__academic_unit', 
            'attendance'
        )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        # 2. FIX: Search by student name OR registration number
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(session_id__icontains=search) |
                Q(student__student_reg_number__icontains=search) | # Fix path to reg_number
                Q(student__person__first_name__icontains=search) | # Search by First Name
                Q(student__person__last_name__icontains=search)  | # Search by Last Name
                Q(class_obj__name__icontains=search)               # Use class_obj name
            ).distinct() # Use distinct to prevent duplicate rows if multiple Q matches
        
        return queryset.order_by('-created_at')
    
   

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # It's better to use the already filtered queryset for stats if that's the intent,
        # but here it looks like you want global stats, which is also fine.
        context['status_choices'] = AttendanceSession.SessionStatus.choices
        context['total_sessions'] = AttendanceSession.objects.count()
        context['pending_sessions'] = AttendanceSession.objects.filter(status='pending').count()
        context['completed_sessions'] = AttendanceSession.objects.filter(status='completed').count()
        context['failed_sessions'] = AttendanceSession.objects.filter(status='failed').count()
        return context


class QuickAttendanceScanView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Quick attendance scan view for kiosk mode
    """
    template_name = 'classroom/quick_scan.html'
    
    # 1. Use the Mixin attribute instead of the decorator
    permission_required = VMSPermissions.ATTENDANCE_CREATE
    
    # 2. Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = Class.objects.filter(is_active=True)
        return context
    
    def post(self, request):
        """Handle QR/OCR scan submission"""
        student_reg = request.POST.get('student_reg')
        class_code = request.POST.get('class_code')
        scan_method = request.POST.get('scan_method', 'qr')
        
        if not student_reg:
            messages.error(request, 'Student registration number is required')
            return redirect('classroom:quick_scan')
        
        # Create and validate session
        service = AttendanceSessionService()
        result = service.process_full_attendance_flow(
            student_reg=student_reg,
            class_code=class_code,
            scan_method=scan_method,
            scan_device='kiosk'
        )
        
        # Check success status based on your service's nested dict structure
        attendance_result = result.get('attendance', {})
        if attendance_result.get('success'):
            messages.success(request, f" Attendance recorded for {attendance_result.get('student_name')}")
        else:
            messages.error(request, f" {attendance_result.get('error', 'Failed to record attendance')}")
        
        return redirect('classroom:quick_scan')


@csrf_exempt
def api_create_attendance_session(request):
    """
    API endpoint for creating attendance session (for ESP32/Scanner)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        student_reg = data.get('student_reg')
        class_code = data.get('class_code')
        scan_method = data.get('scan_method', 'qr')
        scan_device = data.get('scan_device', 'api')
        
        if not student_reg:
            return JsonResponse({'error': 'student_reg required'}, status=400)
        
        service = AttendanceSessionService()
        result = service.create_session(
            student_reg=student_reg,
            class_code=class_code,
            scan_method=scan_method,
            scan_device=scan_device
        )
        
        return JsonResponse(result, status=200 if result['success'] else 400)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_validate_attendance_session(request, session_id):
    """
    API endpoint for validating attendance session
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        service = AttendanceSessionService()
        result = service.validate_session(session_id)
        
        return JsonResponse(result, status=200 if result['success'] else 400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_session_detail_json(request, pk):
    """Get session details as JSON for modal"""
    try:
        session = get_object_or_404(AttendanceSession, pk=pk)
        
        # Calculate time remaining
        if session.expires_at:
            remaining = (session.expires_at - timezone.now()).total_seconds()
            minutes_remaining = int(remaining // 60) if remaining > 0 else 0
        else:
            minutes_remaining = 0
        
        return JsonResponse({
            'id': session.id,
            'session_id': session.session_id,
            'status': session.status,
            'status_display': session.get_status_display(),
            'student_name': session.student.person.full_name() if session.student else session.student_reg_number,
            'student_reg_number': session.student_reg_number,
            'class_name': session.class_obj.academic_unit.name if session.class_obj else session.class_code,
            'class_code': session.class_code,
            'scan_method': session.scan_method,
            'scan_method_display': session.get_scan_method_display(),
            'created_at': session.created_at.isoformat(),
            'expires_at': session.expires_at.isoformat() if session.expires_at else None,
            'minutes_remaining': minutes_remaining,
            'validation_attempts': session.validation_attempts,
            'last_error': session.last_error,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)