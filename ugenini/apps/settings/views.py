# apps/settings/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.utils import timezone
from .forms import (
    GeneralSettingsForm, SecuritySettingsForm, NotificationSettingsForm,
    BackupSettingsForm, ChangePasswordForm
)
from .services import SettingsService, BackupService, AuditLogService


class SettingsBaseView(LoginRequiredMixin, TemplateView):
    """Base view for settings"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access settings.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class SettingsIndexView(SettingsBaseView):
    """Settings dashboard view"""
    template_name = 'settings/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'dashboard'
        return context


class GeneralSettingsView(SettingsBaseView):
    """General settings view"""
    template_name = 'settings/general.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'general'
        
        # Load current settings
        initial_data = {
            'site_name': SettingsService.get_setting('site_name', 'VMS'),
            'site_description': SettingsService.get_setting('site_description', 'Visitor Management System'),
            'timezone': SettingsService.get_setting('timezone', 'Africa/Nairobi'),
            'date_format': SettingsService.get_setting('date_format', 'Y-m-d'),
            'items_per_page': SettingsService.get_setting('items_per_page', 20),
        }
        
        context['form'] = GeneralSettingsForm(initial=initial_data)
        return context
    
    def post(self, request):
        form = GeneralSettingsForm(request.POST)
        if form.is_valid():
            SettingsService.set_setting('site_name', form.cleaned_data['site_name'], 'general')
            SettingsService.set_setting('site_description', form.cleaned_data['site_description'], 'general')
            SettingsService.set_setting('timezone', form.cleaned_data['timezone'], 'general')
            SettingsService.set_setting('time_format', form.cleaned_data['time_format'], 'general')
            SettingsService.set_setting('date_format', form.cleaned_data['date_format'], 'general')
            SettingsService.set_setting('week_start', form.cleaned_data['week_start'], 'general')
            SettingsService.set_setting('language', form.cleaned_data['language'], 'general')
            SettingsService.set_setting('items_per_page', form.cleaned_data['items_per_page'], 'general')
            
            messages.success(request, 'General settings updated successfully.')
            return redirect('settings:general')
        
        return render(request, self.template_name, {'form': form, 'active_tab': 'general'})


class SecuritySettingsView(SettingsBaseView):
    """Security settings view"""
    template_name = 'settings/security.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'security'
        context['password_form'] = ChangePasswordForm(user=self.request.user)
        
        # Load current security settings
        initial_data = {
            'session_timeout': SettingsService.get_setting('session_timeout', 60),
            'max_login_attempts': SettingsService.get_setting('max_login_attempts', 5),
            'password_expiry_days': SettingsService.get_setting('password_expiry_days', 90),
            'two_factor_auth': SettingsService.get_setting('two_factor_auth', 'false') == 'true',
            'require_strong_password': SettingsService.get_setting('require_strong_password', 'true') == 'true',
        }
        
        context['form'] = SecuritySettingsForm(initial=initial_data)
        return context
    
    def post(self, request):
        if 'security_settings' in request.POST:
            form = SecuritySettingsForm(request.POST)
            if form.is_valid():
                SettingsService.set_setting('session_timeout', form.cleaned_data['session_timeout'], 'security')
                SettingsService.set_setting('max_login_attempts', form.cleaned_data['max_login_attempts'], 'security')
                SettingsService.set_setting('password_expiry_days', form.cleaned_data['password_expiry_days'], 'security')
                SettingsService.set_setting('two_factor_auth', str(form.cleaned_data['two_factor_auth']).lower(), 'security')
                SettingsService.set_setting('require_strong_password', str(form.cleaned_data['require_strong_password']).lower(), 'security')
                
                messages.success(request, 'Security settings updated successfully.')
                return redirect('settings:security')
        
        elif 'change_password' in request.POST:
            password_form = ChangePasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('settings:security')
            else:
                return render(request, self.template_name, {
                    'form': SecuritySettingsForm(),
                    'password_form': password_form,
                    'active_tab': 'security'
                })
        
        return redirect('settings:security')


class NotificationSettingsView(SettingsBaseView):
    """Notification settings view"""
    template_name = 'settings/notification.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'notification'
        
        initial_data = {
            'email_notifications': SettingsService.get_setting('email_notifications', 'true') == 'true',
            'sms_notifications': SettingsService.get_setting('sms_notifications', 'false') == 'true',
            'attendance_alerts': SettingsService.get_setting('attendance_alerts', 'true') == 'true',
            'visitor_alerts': SettingsService.get_setting('visitor_alerts', 'true') == 'true',
            'security_alerts': SettingsService.get_setting('security_alerts', 'true') == 'true',
            'notification_email': SettingsService.get_setting('notification_email', 'admin@vms.com'),
        }
        
        context['form'] = NotificationSettingsForm(initial=initial_data)
        return context
    
    def post(self, request):
        form = NotificationSettingsForm(request.POST)
        if form.is_valid():
            SettingsService.set_setting('email_notifications', str(form.cleaned_data['email_notifications']).lower(), 'notification')
            SettingsService.set_setting('sms_notifications', str(form.cleaned_data['sms_notifications']).lower(), 'notification')
            SettingsService.set_setting('attendance_alerts', str(form.cleaned_data['attendance_alerts']).lower(), 'notification')
            SettingsService.set_setting('visitor_alerts', str(form.cleaned_data['visitor_alerts']).lower(), 'notification')
            SettingsService.set_setting('security_alerts', str(form.cleaned_data['security_alerts']).lower(), 'notification')
            SettingsService.set_setting('notification_email', form.cleaned_data['notification_email'], 'notification')
            
            messages.success(request, 'Notification settings updated successfully.')
            return redirect('settings:notification')
        
        return render(request, self.template_name, {'form': form, 'active_tab': 'notification'})


class BackupSettingsView(SettingsBaseView):
    """Backup settings view"""
    template_name = 'settings/backup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'backup'
        context['backup_history'] = BackupService.get_backup_history()
        
        initial_data = {
            'auto_backup': SettingsService.get_setting('auto_backup', 'true') == 'true',
            'backup_frequency': SettingsService.get_setting('backup_frequency', 'daily'),
            'backup_time': SettingsService.get_setting('backup_time', '02:00'),
            'backup_retention_days': SettingsService.get_setting('backup_retention_days', 30),
        }
        
        context['form'] = BackupSettingsForm(initial=initial_data)
        return context
    
    def post(self, request):
        if 'backup_settings' in request.POST:
            form = BackupSettingsForm(request.POST)
            if form.is_valid():
                SettingsService.set_setting('auto_backup', str(form.cleaned_data['auto_backup']).lower(), 'backup')
                SettingsService.set_setting('backup_frequency', form.cleaned_data['backup_frequency'], 'backup')
                SettingsService.set_setting('backup_time', form.cleaned_data['backup_time'], 'backup')
                SettingsService.set_setting('backup_retention_days', form.cleaned_data['backup_retention_days'], 'backup')
                
                messages.success(request, 'Backup settings updated successfully.')
                return redirect('settings:backup')
        
        elif 'create_backup' in request.POST:
            result = BackupService.create_backup(request.user)
            if result['success']:
                messages.success(request, f"Backup created successfully!")
            else:
                messages.error(request, f"Backup failed: {result['error']}")
            return redirect('settings:backup')
        
        return redirect('settings:backup')


class IntegrationSettingsView(SettingsBaseView):
    """Integration settings view"""
    template_name = 'settings/integration.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'integration'
        return context


class AuditLogsView(SettingsBaseView):
    """Audit logs view"""
    template_name = 'settings/audit_logs.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'audit'
        
        logs = AuditLogService.get_audit_logs(days=30)
        paginator = Paginator(logs, 50)
        page_number = self.request.GET.get('page', 1)
        context['logs'] = paginator.get_page(page_number)
        
        return context