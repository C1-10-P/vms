from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, DetailView, UpdateView, ListView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
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
from .models import VisitorSession, Visitor, BLETag, VisitorVisit
from .forms import (
    VisitorSessionForm, VisitorCheckinSessionForm, 
    VisitorTagAssignForm, VisitorOCRProcessForm
)
from .services import VisitorSessionService
from apps.core.models import Person, Staff


class VisitorSessionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    View for creating a new visitor session
    """
    model = VisitorSession
    form_class = VisitorSessionForm
    template_name = 'vms/session_create.html'
    
    # Standard CBV permission check
    permission_required = VMSPermissions.VISITOR_CHECKIN
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Visitor Session'
        context['session_types'] = VisitorSession.SessionType.choices
        return context
    
    def form_valid(self, form):
        session = form.save(commit=False)
        session.session_id = str(uuid.uuid4())
        
        # Robust IP detection
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
            
        session.ip_address = ip
        session.user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        session.save()
        
        messages.success(self.request, f'Visitor session created. Session ID: {session.session_id[:8]}')
        
        # Redirect based on session type
        if session.session_type == 'checkin':
            return redirect('vms:session_checkin', session_id=session.session_id)
        elif session.session_type == 'tag_assign':
            return redirect('vms:session_tag_assign', session_id=session.session_id)
        
        return redirect('vms:session_detail', pk=session.pk)
    
    def get_success_url(self):
        return reverse_lazy('vms:session_list')


class VisitorCheckinSessionView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    View for processing visitor check-in session
    """
    model = VisitorSession
    form_class = VisitorCheckinSessionForm
    template_name = 'vms/session_checkin.html'
    context_object_name = 'session'
    
    # Standard CBV way to enforce permissions
    permission_required = VMSPermissions.VISITOR_CHECKIN
    
    # Removed the @permission_required decorator here
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_object(self):
        return get_object_or_404(VisitorSession, session_id=self.kwargs.get('session_id'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Visitor Check-in'
        context['session_id'] = self.object.session_id
        context['extracted_data'] = self.object.extracted_data
        context['staff_members'] = Staff.objects.select_related('person').filter(is_active=True)
        
        # Calculate time remaining
        if self.object.is_valid():
            remaining = (self.object.expires_at - timezone.now()).total_seconds()
            context['seconds_remaining'] = int(remaining)
            context['minutes_remaining'] = int(remaining // 60)
        else:
            context['seconds_remaining'] = 0
            context['minutes_remaining'] = 0
        
        return context
    
    def form_valid(self, form):
        session = self.object
        
        if not session.is_valid():
            messages.error(self.request, 'Session has expired. Please create a new session.')
            return redirect('vms:session_create')
        
        additional_info = {
            'email': form.cleaned_data.get('email'),
            'phone_number': form.cleaned_data.get('phone_number'),
            'organization': form.cleaned_data.get('organization'),
            'purpose': form.cleaned_data.get('purpose'),
            'host_person_id': form.cleaned_data.get('host_person'),
        }
        
        # Complete check-in using service
        from .services import VisitorSessionService
        service = VisitorSessionService()
        result = service.complete_checkin_session(session.session_id, additional_info)
        
        if result['success']:
            messages.success(self.request, f" Visitor checked in: {result['visitor_name']}")
            
            # If we have a visitor, redirect to tag assignment
            if result.get('visitor_id'):
                return redirect('vms:session_tag_assign', session_id=session.session_id)
            else:
                return redirect('vms:session_detail', pk=session.pk)
        else:
            messages.error(self.request, result.get('error', 'Check-in failed'))
            return self.form_invalid(form)


class VisitorSessionCompleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    View for completing a visitor session (alternative endpoint)
    """
    # Standard CBV way to enforce permissions
    permission_required = VMSPermissions.VISITOR_CHECKIN

    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, session_id):
        """Complete the visitor session"""
        session = get_object_or_404(VisitorSession, session_id=session_id)
        
        if not session.is_valid():
            return JsonResponse({
                'success': False,
                'error': 'Session has expired'
            }, status=400)
        
        # Get additional info from POST data
        additional_info = {
            'email': request.POST.get('email'),
            'phone_number': request.POST.get('phone_number'),
            'organization': request.POST.get('organization'),
            'purpose': request.POST.get('purpose', 'meeting'),
            'host_person_id': request.POST.get('host_person_id'),
        }
        
        from .services import VisitorSessionService
        service = VisitorSessionService()
        result = service.complete_checkin_session(session_id, additional_info)
        
        if result['success']:
            messages.success(request, f"✓ Visitor checked in: {result['visitor_name']}")
            return redirect('vms:session_tag_assign', session_id=session_id)
        else:
            messages.error(request, result.get('error', 'Check-in failed'))
            return redirect('vms:session_checkin', session_id=session_id)
    
    def get(self, request, session_id):
        """GET method - show completion form"""
        session = get_object_or_404(VisitorSession, session_id=session_id)
        
        context = {
            'session': session,
            'title': 'Complete Visitor Check-in',
            'extracted_data': session.extracted_data,
            'staff_members': Staff.objects.select_related('person').filter(is_active=True),
        }
        return render(request, 'vms/session_complete.html', context)


class VisitorTagAssignView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    View for assigning BLE tag to visitor session
    """
    # Standard CBV way to enforce permissions
    permission_required = VMSPermissions.VISITOR_CHECKIN
    
    # Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, session_id):
        """GET method - show tag assignment form"""
        session = get_object_or_404(VisitorSession, session_id=session_id)
        
        if not session.visitor:
            messages.error(request, 'No visitor associated with this session. Please complete check-in first.')
            return redirect('vms:session_checkin', session_id=session_id)
        
        context = {
            'session': session,
            'title': 'Assign BLE Tag to Visitor',
            'visitor': session.visitor,
            'available_tags': BLETag.objects.filter(status='available'),
            'form': VisitorTagAssignForm(),
        }
        return render(request, 'vms/session_tag_assign.html', context)
    
    def post(self, request, session_id):
        """POST method - assign tag"""
        session = get_object_or_404(VisitorSession, session_id=session_id)
        
        if not session.is_valid():
            messages.error(request, 'Session has expired. Please create a new session.')
            return redirect('vms:session_create')
        
        form = VisitorTagAssignForm(request.POST)
        
        if form.is_valid():
            tag_uuid = form.cleaned_data['tag_uuid']
            
            from .services import VisitorSessionService
            service = VisitorSessionService()
            result = service.complete_tag_assignment(session_id, tag_uuid)
            
            if result['success']:
                # Using full_name from related person record
                name = session.visitor.person.full_name if session.visitor.person else "Visitor"
                messages.success(request, f"✓ Tag {tag_uuid} assigned to {name}")
                
                # Mark session as completed
                session.mark_completed()
                
                return redirect('vms:session_detail', pk=session.pk)
            else:
                messages.error(request, result.get('error', 'Tag assignment failed'))
        else:
            messages.error(request, 'Please provide a valid tag UUID')
        
        # Re-render with errors
        context = {
            'session': session,
            'title': 'Assign BLE Tag to Visitor',
            'visitor': session.visitor,
            'available_tags': BLETag.objects.filter(status='available'),
            'form': form,
        }
        return render(request, 'vms/session_tag_assign.html', context)


class VisitorSessionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Visitor session detail view
    """
    model = VisitorSession
    template_name = 'vms/session_detail.html'
    context_object_name = 'session'
    
    # 1. Correct permission handling for CBVs
    permission_required = VMSPermissions.VISITOR_VIEW
    
    # 2. Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate time remaining
        if self.object.is_valid():
            remaining = (self.object.expires_at - timezone.now()).total_seconds()
            context['seconds_remaining'] = int(remaining)
            context['minutes_remaining'] = int(remaining // 60)
        else:
            context['seconds_remaining'] = 0
            context['minutes_remaining'] = 0
        
        # Get available tags if awaiting tag
        if self.object.status == 'awaiting_tag':
            context['available_tags'] = BLETag.objects.filter(status='available')
        
        # Get related records
        if self.object.visitor:
            context['visitor'] = self.object.visitor
            # Good use of select_related/prefetch_related would be even better here!
            context['visits'] = self.object.visitor.visits.all().order_by('-check_in_time')[:10]
        
        if self.object.assigned_tag:
            context['assigned_tag'] = self.object.assigned_tag
        
        # Get session timeline
        context['timeline'] = self.get_session_timeline()
        
        return context
    
    def get_session_timeline(self):
        """Generate timeline of session events"""
        timeline = []
        
        # Creation
        timeline.append({
            'event': 'Session Created',
            'timestamp': self.object.created_at,
            'description': f'Session {self.object.get_session_type_display()} created',
            'icon': 'plus-circle',
            'color': 'primary'
        })
        
        # Status changes
        if self.object.validated_at:
            timeline.append({
                'event': 'Validated',
                'timestamp': self.object.validated_at,
                'description': 'Session validated successfully',
                'icon': 'check-circle',
                'color': 'success'
            })
        
        if self.object.completed_at:
            timeline.append({
                'event': 'Completed',
                'timestamp': self.object.completed_at,
                'description': 'Session completed',
                'icon': 'check-double',
                'color': 'success'
            })
        
        # Visitor created
        if self.object.visitor:
            timeline.append({
                'event': 'Visitor Recorded',
                'timestamp': self.object.visitor.created_at,
                'description': f'Visitor: {self.object.visitor.person.full_name}',
                'icon': 'user',
                'color': 'info'
            })
        
        # Tag assigned
        if self.object.assigned_tag:
            timeline.append({
                'event': 'Tag Assigned',
                'timestamp': self.object.assigned_tag.updated_at,
                'description': f'Tag: {self.object.assigned_tag.tag_uuid}',
                'icon': 'tag',
                'color': 'warning'
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        return timeline


class VisitorSessionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List all visitor sessions
    """
    model = VisitorSession
    ordering = ['-created_at']
    template_name = 'vms/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    # 1. Standard CBV permission check
    permission_required = VMSPermissions.VISITOR_VIEW
    
    # 2. Removed the @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        # Good use of select_related for performance!
        queryset = VisitorSession.objects.select_related('visitor__person', 'assigned_tag')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by type
        session_type = self.request.GET.get('session_type')
        if session_type:
            queryset = queryset.filter(session_type=session_type)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        # ... (rest of filtering logic)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(session_id__icontains=search) |
                Q(visitor__person__first_name__icontains=search) |
                Q(visitor__person__last_name__icontains=search) |
                Q(extracted_data__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = VisitorSession.SessionStatus.choices
        context['type_choices'] = VisitorSession.SessionType.choices
        context['total_sessions'] = VisitorSession.objects.count()
        context['pending_sessions'] = VisitorSession.objects.filter(status='pending').count()
        context['completed_sessions'] = VisitorSession.objects.filter(status='completed').count()
        context['expired_sessions'] = VisitorSession.objects.filter(status='expired').count()
        return context


class VisitorOCRProcessView(LoginRequiredMixin, TemplateView):
    """
    View for processing OCR scanned ID for visitor check-in
    """
    template_name = 'vms/ocr_process.html'
    
    # 1. Standard CBV permission check
    permission_required = VMSPermissions.VISITOR_CHECKIN
    
    # 2. Removed the @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = VisitorOCRProcessForm()
        return context
    
    def post(self, request):
        form = VisitorOCRProcessForm(request.POST, request.FILES)
        
        if form.is_valid():
            from apps.firmware.ocr_service import ocr_service
            
            image = request.FILES.get('id_image')
            if image:
                result = ocr_service.process_id_image(image.read(), 'auto')
                
                if result['success']:
                    # Create session with extracted data
                    from .services import VisitorSessionService
                    service = VisitorSessionService()
                    session_result = service.create_checkin_session(
                        extracted_data=result['extracted_data'],
                        scan_device='ocr_scanner'
                    )
                    
                    if session_result['success']:
                        messages.success(request, 'ID scanned successfully. Please complete visitor information.')
                        return redirect('vms:session_complete', session_id=session_result['session_id'])
                    else:
                        messages.error(request, session_result.get('error', 'Failed to create session'))
                else:
                    messages.error(request, result.get('error', 'OCR processing failed'))
            else:
                messages.error(request, 'No image provided')
        
        return render(request, self.template_name, {'form': form})


# ============ API Endpoints ============

@csrf_exempt
def api_create_visitor_session(request):
    """
    API endpoint for creating visitor session
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        extracted_data = data.get('extracted_data', {})
        scan_device = data.get('scan_device', 'api')
        
        from .services import VisitorSessionService
        service = VisitorSessionService()
        result = service.create_checkin_session(
            extracted_data=extracted_data,
            scan_device=scan_device
        )
        
        return JsonResponse(result, status=200 if result['success'] else 400)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_complete_visitor_session(request, session_id):
    """
    API endpoint for completing visitor session
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body) if request.body else {}
        additional_info = data.get('additional_info', {})
        
        from .services import VisitorSessionService
        service = VisitorSessionService()
        result = service.complete_checkin_session(session_id, additional_info)
        
        return JsonResponse(result, status=200 if result['success'] else 400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_assign_tag_to_session(request, session_id):
    """
    API endpoint for assigning tag to session
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        tag_uuid = data.get('tag_uuid')
        
        if not tag_uuid:
            return JsonResponse({'error': 'tag_uuid required'}, status=400)
        
        from .services import VisitorSessionService
        service = VisitorSessionService()
        result = service.complete_tag_assignment(session_id, tag_uuid)
        
        return JsonResponse(result, status=200 if result['success'] else 400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_get_session_status(request, session_id):
    """
    API endpoint for getting session status
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        session = get_object_or_404(VisitorSession, session_id=session_id)
        
        return JsonResponse({
            'success': True,
            'session_id': session.session_id,
            'status': session.status,
            'session_type': session.session_type,
            'is_valid': session.is_valid(),
            'expires_at': session.expires_at.isoformat(),
            'visitor_id': session.visitor.id if session.visitor else None,
            'visitor_name': session.visitor.person.full_name if session.visitor else None,
            'tag_assigned': session.assigned_tag is not None,
            'tag_uuid': session.assigned_tag.tag_uuid if session.assigned_tag else None,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_session_detail_json(request, pk):
    """Return session details as JSON for modal"""
    try:
        session = VisitorSession.objects.select_related('visitor__person', 'assigned_tag').get(pk=pk)
        
        # Calculate time remaining
        if session.expires_at:
            remaining = (session.expires_at - timezone.now()).total_seconds()
            minutes_remaining = int(remaining // 60) if remaining > 0 else 0
        else:
            minutes_remaining = 0
        
        data = {
            'id': session.id,
            'session_id': session.session_id,
            'session_type': session.session_type,
            'session_type_display': session.get_session_type_display(),
            'status': session.status,
            'status_display': session.get_status_display(),
            'created_at': session.created_at.isoformat(),
            'expires_at': session.expires_at.isoformat() if session.expires_at else None,
            'minutes_remaining': minutes_remaining,
            'visitor': {
                'id': session.visitor.id if session.visitor else None,
                'name': f"{session.visitor.person.first_name or ''} {session.visitor.person.last_name or ''}".strip() if session.visitor and session.visitor.person else None,
                'organization': session.visitor.organization if session.visitor else None,
                'id_number': session.visitor.id_number if session.visitor else None,
                'host': str(session.visitor.host_person) if session.visitor and session.visitor.host_person else None,
            } if session.visitor else None,
            'assigned_tag': {
                'tag_uuid': session.assigned_tag.tag_uuid,
                'status': session.assigned_tag.status,
            } if session.assigned_tag else None,
            'extracted_data': session.extracted_data,
            'timeline': get_session_timeline_data(session),
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def get_session_timeline_data(session):
    """Helper to generate timeline data for JSON"""
    timeline = []
    
    timeline.append({
        'event': 'Session Created',
        'timestamp': session.created_at.isoformat(),
        'description': f'{session.get_session_type_display()} session created',
        'icon': 'plus-circle',
        'color': 'primary'
    })
    
    if session.validated_at:
        timeline.append({
            'event': 'Validated',
            'timestamp': session.validated_at.isoformat(),
            'description': 'Session validated',
            'icon': 'check-circle',
            'color': 'success'
        })
    
    if session.completed_at:
        timeline.append({
            'event': 'Completed',
            'timestamp': session.completed_at.isoformat(),
            'description': 'Session completed',
            'icon': 'check-double',
            'color': 'success'
        })
    
    if session.visitor and session.visitor.created_at:
        name = f"{session.visitor.person.first_name or ''} {session.visitor.person.last_name or ''}".strip() if session.visitor.person else 'Visitor'
        timeline.append({
            'event': 'Visitor Recorded',
            'timestamp': session.visitor.created_at.isoformat(),
            'description': f'Visitor: {name}',
            'icon': 'user',
            'color': 'info'
        })
    
    if session.assigned_tag and session.assigned_tag.updated_at:
        timeline.append({
            'event': 'Tag Assigned',
            'timestamp': session.assigned_tag.updated_at.isoformat(),
            'description': f'Tag: {session.assigned_tag.tag_uuid}',
            'icon': 'tag',
            'color': 'warning'
        })
    
    timeline.sort(key=lambda x: x['timestamp'])
    return timeline


@csrf_exempt
def process_ocr_image(request):
    """Process OCR image and extract data"""
    if request.method == 'POST':
        image = request.FILES.get('image')
        id_type = request.POST.get('id_type')
        session_id = request.POST.get('session_id')
        
        try:
            session = VisitorSession.objects.get(session_id=session_id)
            
            # Store captured image
            session.captured_image = image
            session.id_type = id_type
            session.save()
            
            # Simulate OCR extraction (replace with actual OCR service)
            # In production, integrate with a real OCR service like Google Vision, Tesseract, etc.
            extracted_data = {
                'full_name': 'John Doe',
                'first_name': 'John',
                'last_name': 'Doe',
                'id_number': '12345678',
                'dob': '1990-01-01',
            }
            
            session.extracted_data = extracted_data
            session.raw_ocr_text = "Simulated OCR text"
            session.status = 'awaiting_info'
            session.save()
            
            return JsonResponse({'success': True, 'data': extracted_data})
        except VisitorSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
def complete_checkin_session(request):
    """Complete the check-in process"""
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        organization = request.POST.get('organization')
        purpose = request.POST.get('purpose')
        host_person_id = request.POST.get('host_person_id')
        
        try:
            session = VisitorSession.objects.get(session_id=session_id)
            
            # Create or get visitor
            extracted = session.extracted_data
            person = Person.objects.create(
                first_name=extracted.get('first_name', ''),
                last_name=extracted.get('last_name', ''),
                email=email or '',
                phone_number=phone_number or '',
                person_type='visitor'
            )
            
            visitor = Visitor.objects.create(
                person=person,
                id_number=extracted.get('id_number', ''),
                organization=organization or '',
                purpose=purpose or 'meeting',
                host_person_id=host_person_id or None
            )
            
            # Create visit record
            visit = VisitorVisit.objects.create(
                visitor=visitor,
                check_in_time=timezone.now(),
                purpose=purpose or 'meeting',
                host_person_id=host_person_id or None,
                status='active'
            )
            
            session.visitor = visitor
            session.visit = visit
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            return JsonResponse({
                'success': True,
                'visitor_name': person.full_name,
                'id_number': visitor.id_number,
                'visitor_id': visitor.id
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
def assign_tag_to_session(request, session_id):
    """Assign BLE tag to visitor session"""
    if request.method == 'POST':
        visitor_id = request.POST.get('visitor_id')
        tag_uuid = request.POST.get('tag_uuid')
        
        try:
            session = VisitorSession.objects.get(session_id=session_id)
            
            # Get or find visitor by ID
            if visitor_id.isdigit():
                visitor = Visitor.objects.get(id=visitor_id)
            else:
                visitor = Visitor.objects.get(id_number=visitor_id)
            
            # Get tag
            tag = BLETag.objects.get(tag_uuid=tag_uuid, status='available')
            
            # Assign tag
            result = session.assign_tag(tag)
            
            if result['success']:
                return JsonResponse({'success': True, 'message': 'Tag assigned successfully'})
            else:
                return JsonResponse({'success': False, 'error': 'Tag assignment failed'})
        except Visitor.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Visitor not found'})
        except BLETag.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Tag not available'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def create_checkin_session(request):
    """Create check-in session with extracted data"""
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        extracted_data = json.loads(request.POST.get('extracted_data', '{}'))
        
        try:
            session = VisitorSession.objects.get(session_id=session_id)
            session.extracted_data = extracted_data
            session.status = 'awaiting_info'
            session.save()
            return JsonResponse({'success': True})
        except VisitorSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
    return JsonResponse({'success': False})


def get_session_data(request, session_id):
    """Get session data for resuming"""
    try:
        session = VisitorSession.objects.get(session_id=session_id)
        return JsonResponse({
            'first_name': session.extracted_data.get('first_name', ''),
            'last_name': session.extracted_data.get('last_name', ''),
            'id_number': session.extracted_data.get('id_number', ''),
            'dob': session.extracted_data.get('dob', ''),
            'phone_number': session.provided_info.get('phone_number', ''),
            'email': session.provided_info.get('email', ''),
            'organization': session.provided_info.get('organization', ''),
            'purpose': session.provided_info.get('purpose', 'meeting'),
            'host_person_id': session.provided_info.get('host_person_id', ''),
        })
    except VisitorSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)