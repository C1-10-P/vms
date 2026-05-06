from django.db import models
from django.utils import timezone
from apps.core.models.base import BaseModel

class Report(BaseModel):
    """
    Generated report definitions and instances.
    """
    
    class ReportType(models.TextChoices):
        ATTENDANCE_DAILY = 'attendance_daily', 'Daily Attendance'
        ATTENDANCE_WEEKLY = 'attendance_weekly', 'Weekly Attendance'
        ATTENDANCE_MONTHLY = 'attendance_monthly', 'Monthly Attendance'
        VISITOR_DAILY = 'visitor_daily', 'Daily Visitors'
        VISITOR_WEEKLY = 'visitor_weekly', 'Weekly Visitors'
        ACCESS_SUMMARY = 'access_summary', 'Access Summary'
        SECURITY_AUDIT = 'security_audit', 'Security Audit'
        DEVICE_HEALTH = 'device_health', 'Device Health Report'
        OCCUPANCY = 'occupancy', 'Occupancy Report'
    
    class Format(models.TextChoices):
        PDF = 'pdf', 'PDF'
        EXCEL = 'excel', 'Excel'
        CSV = 'csv', 'CSV'
        JSON = 'json', 'JSON'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    # Report definition
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=30, choices=ReportType.choices, db_index=True)
    
    # Parameters
    parameters = models.JSONField(
        default=dict,
        help_text="Report parameters (date range, filters, etc.)"
    )
    
    # Generation
    format = models.CharField(max_length=10, choices=Format.choices, default=Format.PDF)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # File
    generated_file = models.FileField(upload_to='reports/', null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Requestor
    requested_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_reports'
    )
    
    # Results
    row_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    # Delivery
    delivered_via = models.CharField(max_length=50, blank=True)
    delivered_to = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['requested_by', 'requested_at']),
            models.Index(fields=['status', 'requested_at']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.requested_at.date()}"
    
    def mark_completed(self, file_path, row_count=0):
        """Mark report as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.row_count = row_count
        self.generated_file = file_path
        self.save()
    
    def mark_failed(self, error):
        """Mark report as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error
        self.save()


class ReportSchedule(BaseModel):
    """
    Scheduled report generation.
    """
    
    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
    
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=30, choices=Report.ReportType.choices)
    
    # Schedule
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    day_of_week = models.PositiveSmallIntegerField(null=True, blank=True, help_text="0=Monday")
    day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)
    time_of_day = models.TimeField(default='08:00')
    
    # Parameters
    parameters = models.JSONField(default=dict)
    format = models.CharField(max_length=10, choices=Report.Format.choices, default=Report.Format.PDF)
    
    # Delivery
    email_recipients = models.JSONField(default=list, help_text="List of email addresses")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'next_run']),
            models.Index(fields=['report_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def calculate_next_run(self):
        """Calculate next run time"""
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if self.frequency == 'daily':
            next_date = now.date() + timedelta(days=1)
        elif self.frequency == 'weekly':
            days_ahead = (self.day_of_week - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_date = now.date() + timedelta(days=days_ahead)
        elif self.frequency == 'monthly':
            if now.day < self.day_of_month:
                next_date = now.date().replace(day=self.day_of_month)
            else:
                next_month = now.date().replace(day=1) + timedelta(days=32)
                next_date = next_month.replace(day=min(self.day_of_month, 28))
        else:
            return None
        
        self.next_run = datetime.combine(next_date, self.time_of_day)
        self.save()
        return self.next_run


class ExportLog(BaseModel):
    """
    Log of data exports for audit trail.
    """
    
    class ExportType(models.TextChoices):
        ATTENDANCE = 'attendance', 'Attendance Data'
        VISITORS = 'visitors', 'Visitor Data'
        ACCESS_LOGS = 'access_logs', 'Access Logs'
        DEVICE_DATA = 'device_data', 'Device Data'
    
    export_type = models.CharField(max_length=20, choices=ExportType.choices)
    
    # Export details
    filters = models.JSONField(default=dict, help_text="Filters applied to export")
    row_count = models.PositiveIntegerField(default=0)
    format = models.CharField(max_length=10, choices=Report.Format.choices)
    
    # File
    exported_file = models.FileField(upload_to='exports/', null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    # User
    exported_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='exports'
    )
    
    # IP and source
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Reason
    reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['export_type', 'created_at']),
            models.Index(fields=['exported_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_export_type_display()} export by {self.exported_by} at {self.created_at}"