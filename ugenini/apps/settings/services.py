# apps/settings/services.py
import json
import subprocess
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from .models import SystemSetting, BackupHistory, AuditLog


class SettingsService:
    """Service for managing system settings"""
    
    @staticmethod
    def get_setting(key, default=None):
        """Get a setting value by key"""
        cache_key = f'setting_{key}'
        value = cache.get(cache_key)
        
        if value is None:
            try:
                setting = SystemSetting.objects.get(setting_key=key)
                value = setting.setting_value
                cache.set(cache_key, value, 3600)
            except SystemSetting.DoesNotExist:
                value = default
        return value
    
    @staticmethod
    def set_setting(key, value, setting_type='general', description=''):
        """Set a setting value"""
        setting, created = SystemSetting.objects.update_or_create(
            setting_key=key,
            defaults={
                'setting_value': str(value),
                'setting_type': setting_type,
                'description': description
            }
        )
        cache.delete(f'setting_{key}')
        return setting
    
    @staticmethod
    def get_all_settings():
        """Get all settings grouped by type"""
        settings_dict = {}
        for setting in SystemSetting.objects.all():
            if setting.setting_type not in settings_dict:
                settings_dict[setting.setting_type] = {}
            settings_dict[setting.setting_type][setting.setting_key] = setting.setting_value
        return settings_dict


class BackupService:
    """Service for database backup operations"""
    
    @staticmethod
    def create_backup(user=None):
        """Create a database backup"""
        backup = BackupHistory.objects.create(
            backup_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            status='in_progress',
            created_by=user
        )
        
        try:
            # Create backup directory
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(backup_dir, f"{backup.backup_name}.sql")
            
            # Execute database backup command
            if 'sqlite3' in settings.DATABASES['default']['ENGINE']:
                # SQLite backup
                import shutil
                shutil.copy2(settings.DATABASES['default']['NAME'], backup_file)
            else:
                # PostgreSQL/MySQL backup
                db_settings = settings.DATABASES['default']
                cmd = f"mysqldump -u {db_settings['USER']} -p{db_settings['PASSWORD']} {db_settings['NAME']} > {backup_file}"
                subprocess.run(cmd, shell=True, check=True)
            
            # Calculate file size
            backup_size = os.path.getsize(backup_file)
            
            backup.backup_file = backup_file
            backup.backup_size = backup_size
            backup.status = 'success'
            backup.completed_at = timezone.now()
            backup.save()
            
            return {'success': True, 'backup_id': backup.id, 'file': backup_file}
            
        except Exception as e:
            backup.status = 'failed'
            backup.error_message = str(e)
            backup.completed_at = timezone.now()
            backup.save()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_backup_history(limit=50):
        """Get backup history"""
        return BackupHistory.objects.all()[:limit]
    
    @staticmethod
    def restore_backup(backup_id):
        """Restore from backup"""
        try:
            backup = BackupHistory.objects.get(id=backup_id)
            if not os.path.exists(backup.backup_file):
                return {'success': False, 'error': 'Backup file not found'}
            
            # Execute restore command
            db_settings = settings.DATABASES['default']
            cmd = f"mysql -u {db_settings['USER']} -p{db_settings['PASSWORD']} {db_settings['NAME']} < {backup.backup_file}"
            subprocess.run(cmd, shell=True, check=True)
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class AuditLogService:
    """Service for audit logging"""
    
    @staticmethod
    def log_action(user, action, model_name='', object_id='', changes=None, request=None):
        """Log an action to audit log"""
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else '',
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def get_audit_logs(days=30):
        """Get audit logs for recent days"""
        cutoff = timezone.now() - timedelta(days=days)
        return AuditLog.objects.filter(created_at__gte=cutoff).order_by('-created_at')