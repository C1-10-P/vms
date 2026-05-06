# apps/settings/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import SystemSetting


class GeneralSettingsForm(forms.Form):
    site_name = forms.CharField(max_length=100, required=True)
    site_description = forms.CharField(max_length=500, required=False)
    timezone = forms.CharField(max_length=50, required=True)
    time_format = forms.ChoiceField(choices=[('24h', '24-hour'), ('12h', '12-hour')], required=True)
    date_format = forms.CharField(max_length=20, required=True)
    week_start = forms.ChoiceField(choices=[('monday', 'Monday'), ('sunday', 'Sunday'), ('saturday', 'Saturday')], required=True)
    language = forms.ChoiceField(choices=[('en', 'English'), ('fr', 'French'), ('sw', 'Swahili'), ('rw', 'Kinyarwanda')], required=True)
    items_per_page = forms.IntegerField(required=True)


class SecuritySettingsForm(forms.Form):
    """Security settings form"""
    session_timeout = forms.IntegerField(min_value=5, max_value=480, required=False, 
                                         widget=forms.NumberInput(attrs={'class': 'form-input'}),
                                         help_text="Session timeout in minutes")
    max_login_attempts = forms.IntegerField(min_value=3, max_value=10, required=False,
                                           widget=forms.NumberInput(attrs={'class': 'form-input'}))
    password_expiry_days = forms.IntegerField(min_value=30, max_value=365, required=False,
                                             widget=forms.NumberInput(attrs={'class': 'form-input'}))
    two_factor_auth = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    require_strong_password = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class NotificationSettingsForm(forms.Form):
    """Notification settings form"""
    email_notifications = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    sms_notifications = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    attendance_alerts = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    visitor_alerts = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    security_alerts = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    notification_email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-input'}))


class BackupSettingsForm(forms.Form):
    """Backup settings form"""
    auto_backup = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    backup_frequency = forms.ChoiceField(choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], required=False, widget=forms.Select(attrs={'class': 'form-input'}))
    backup_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}))
    backup_retention_days = forms.IntegerField(min_value=7, max_value=90, required=False,
                                               widget=forms.NumberInput(attrs={'class': 'form-input'}))


class ChangePasswordForm(PasswordChangeForm):
    """Change password form"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-input'})