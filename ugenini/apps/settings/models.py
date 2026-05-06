# apps/settings/models.py
from django.db import models
from django.conf import settings
from apps.core.models.base import BaseModel


class SystemSetting(BaseModel):
    """System settings model"""
    
    class SettingType(models.TextChoices):
        GENERAL = 'general', 'General'
        SECURITY = 'security', 'Security'
        NOTIFICATION = 'notification', 'Notification'
        INTEGRATION = 'integration', 'Integration'
    
    setting_key = models.CharField(max_length=100, unique=True, db_index=True)
    setting_value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SettingType.choices, default=SettingType.GENERAL)
    description = models.TextField(blank=True)
    is_encrypted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['setting_key']
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"{self.setting_key} = {self.setting_value[:50]}"


class BackupHistory(BaseModel):
    """Backup history model"""
    
    class BackupStatus(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        IN_PROGRESS = 'in_progress', 'In Progress'
    
    backup_name = models.CharField(max_length=200)
    backup_file = models.CharField(max_length=500)
    backup_size = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=BackupStatus.choices, default=BackupStatus.IN_PROGRESS)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Backup History'
        verbose_name_plural = 'Backup Histories'
    
    def __str__(self):
        return f"{self.backup_name} - {self.status}"


class AuditLog(BaseModel):
    """Audit log for system activities"""
    
    class ActionType(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        EXPORT = 'export', 'Export'
        IMPORT = 'import', 'Import'
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ActionType.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.user} - {self.action} at {self.created_at}"