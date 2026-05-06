from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models.base import TimeStampedModel
from apps.core.models.person import Student
from apps.core.models.academic import Class
from apps.firmware.models.edge_node import EdgeNode

class ClassAttendance(TimeStampedModel):
    """
    Record of student attendance for a class session.
    """
    class VerificationMethod(models.TextChoices):
        RFID = 'rfid', 'RFID Card'
        # FACE = 'face', 'Face Recognition'
        BAR_CODE = 'bar_code', 'Bar Code'
        QR = 'qr', 'QR Code'
        MANUAL = 'manual', 'Manual Entry'
        BLE = 'ble', 'BLE Tag'
        NFC = 'nfc', 'NFC'
    
    class VerificationStatus(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        PENDING = 'pending', 'Pending'
        FRAUD_SUSPECTED = 'fraud_suspected', 'Fraud Suspected'
        DUPLICATE = 'duplicate', 'Duplicate Entry'
    
    # Core fields
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='attendances',
        db_index=True
    )
    class_obj = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name='attendances',
        db_index=True
    )
    node = models.ForeignKey(
        EdgeNode, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='attendances'
    )
    
    # Timestamps
    scan_time = models.DateTimeField(
        db_index=True,
        help_text="When the attendance was recorded"
    )
    scan_date = models.DateField(
        db_index=True,
        help_text="Date extracted from scan_time"
    )
    
    # Verification
    verification_method = models.CharField(
        max_length=20, 
        choices=VerificationMethod.choices,
        default=VerificationMethod.MANUAL
    )
    verification_status = models.CharField(
        max_length=20, 
        choices=VerificationStatus.choices,
        default=VerificationStatus.SUCCESS,
        db_index=True
    )
    confidence_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="For biometric methods"
    )
    
    # Geolocation
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Additional data
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw data from scanner/reader"
    )
    remarks = models.TextField(blank=True)
    
    # Audit
    recorded_by = models.ForeignKey(
        'core.Staff', 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='recorded_attendances'
    )
    
    class Meta:
        ordering = ['-scan_time']
        verbose_name = "Class Attendance"
        verbose_name_plural = "Class Attendances"
        indexes = [
            models.Index(fields=['scan_date']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['student', 'scan_date']),
            models.Index(fields=['class_obj', 'scan_date']),
            models.Index(fields=['node', 'scan_time']),
            # Composite indexes for common queries
            models.Index(fields=['student', 'class_obj', 'scan_date']),
            models.Index(fields=['class_obj', 'verification_status']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-populate scan_date from scan_time"""
        if self.scan_time and not self.scan_date:
            self.scan_date = self.scan_time.date()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student.student_reg_number} - {self.class_obj.class_code} - {self.scan_time}"


class DailyAttendanceSummary(TimeStampedModel):
    """
    Pre-computed daily attendance summary for reporting.
    """
    class_obj = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name='daily_summaries'
    )
    summary_date = models.DateField(db_index=True)
    
    # Counts
    total_students = models.PositiveIntegerField(default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    
    # Percentages
    attendance_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Breakdown by time
    morning_sessions = models.PositiveIntegerField(default=0)
    afternoon_sessions = models.PositiveIntegerField(default=0)
    evening_sessions = models.PositiveIntegerField(default=0)
    
    # Metadata
    generated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-summary_date']
        verbose_name = "Daily Attendance Summary"
        verbose_name_plural = "Daily Attendance Summaries"
        unique_together = [['class_obj', 'summary_date']]
        indexes = [
            models.Index(fields=['summary_date', 'class_obj']),
            models.Index(fields=['attendance_percentage']),
        ]
    
    def __str__(self):
        return f"{self.class_obj.class_code} - {self.summary_date}: {self.present_count}/{self.total_students}"


class VerificationLog(TimeStampedModel):
    """
    Detailed log of verification attempts (successful and failed).
    Used for security auditing and fraud detection.
    """
    class VerificationEventType(models.TextChoices):
        ATTEMPT = 'attempt', 'Attempt'
        SUCCESS = 'success', 'Success'
        FAILURE = 'failure', 'Failure'
        RETRY = 'retry', 'Retry'
        BLOCKED = 'blocked', 'Blocked'
    
    # Linked records
    attendance = models.ForeignKey(
        ClassAttendance, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='verification_logs'
    )
    student = models.ForeignKey(
        Student, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='verification_logs'
    )
    node = models.ForeignKey(
        EdgeNode, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='verification_logs'
    )
    
    # Event details
    event_type = models.CharField(
        max_length=20, 
        choices=VerificationEventType.choices,
        db_index=True
    )
    method = models.CharField(
        max_length=20, 
        choices=ClassAttendance.VerificationMethod.choices
    )
    
    # Result
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=255, blank=True)
    
    # Images/data
    captured_image = models.ImageField(
        upload_to='verification/captures/',
        null=True,
        blank=True
    )
    extracted_data = models.JSONField(default=dict, blank=True)
    
    # Timing
    attempt_time = models.DateTimeField(auto_now_add=True, db_index=True)
    processing_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time taken to process in milliseconds"
    )
    
    class Meta:
        ordering = ['-attempt_time']
        verbose_name = "Verification Log"
        verbose_name_plural = "Verification Logs"
        indexes = [
            models.Index(fields=['attempt_time']),
            models.Index(fields=['event_type', 'success']),
            models.Index(fields=['node', 'attempt_time']),
            models.Index(fields=['student', 'attempt_time']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.method} - {'Success' if self.success else 'Failed'}"
    
    
