from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import Notification, SMSLog, EmailLog, USSDSession
from .services import NotificationService


class NotificationListView(LoginRequiredMixin, ListView):
    """
    List user notifications
    """
    model = Notification
    ordering = ['-created_at']
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        if hasattr(self.request.user, 'person'):
            return Notification.objects.filter(
                recipient=self.request.user.person
            ).order_by('-created_at')
        return Notification.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = self.get_queryset().filter(status='pending').count()
        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """
    Notification detail view
    """
    model = Notification
    template_name = 'notifications/detail.html'
    context_object_name = 'notification'
    
    def get_object(self):
        obj = super().get_object()
        if obj.status == 'pending':
            obj.status = 'read'
            obj.read_at = timezone.now()
            obj.save()
        return obj


class NotificationMarkReadView(LoginRequiredMixin, UpdateView):
    """
    Mark notification as read
    """
    model = Notification
    fields = []
    success_url = reverse_lazy('notifications:list')
    
    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})


class SMSLogListView(LoginRequiredMixin, ListView):
    """
    View SMS logs (admin only)
    """
    model = SMSLog
    ordering = ['-created_at']
    template_name = 'notifications/sms_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    @permission_required(VMSPermissions.SYSTEM_VIEW_LOGS)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-queued_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date
        date = self.request.GET.get('date')
        if date:
            queryset = queryset.filter(queued_at__date=date)
        
        return queryset


class EmailLogListView(LoginRequiredMixin, ListView):
    """
    View email logs (admin only)
    """
    model = EmailLog
    ordering = ['-created_at']
    template_name = 'notifications/email_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    @permission_required(VMSPermissions.SYSTEM_VIEW_LOGS)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return super().get_queryset().order_by('-queued_at')


@csrf_exempt
def ussd_callback(request):
    """
    USSD callback endpoint for 2FA and visitor services
    """
    if request.method == 'POST':
        session_id = request.POST.get('sessionId')
        service_code = request.POST.get('serviceCode')
        phone_number = request.POST.get('phoneNumber')
        text = request.POST.get('text', '')
        
        # Process USSD input
        from .services import USSDServic