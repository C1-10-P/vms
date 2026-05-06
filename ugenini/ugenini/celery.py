# vms_project/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ugenini.settings.production')

app = Celery('vms_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    'generate-daily-summary': {
        'task': 'apps.attendance.tasks.generate_daily_summary',
        'schedule': crontab(hour=23, minute=59),  # End of day
    },
    'generate-weekly-report': {
        'task': 'apps.attendance.tasks.generate_weekly_report',
        'schedule': crontab(day_of_week=0, hour=0, minute=0),  # Sunday midnight
    },
    'cleanup-old-records': {
        'task': 'apps.attendance.tasks.cleanup_old_ledger_entries',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # 1st of month
    },
    'check-node-health': {
        'task': 'apps.devices.tasks.check_node_health',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'sync-offline-data': {
        'task': 'apps.devices.tasks.sync_offline_data',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'backup-database': {
        'task': 'apps.core.tasks.backup_database',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')