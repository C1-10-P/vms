from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
import uuid

from apps.core.models.base import BaseModel


class AttendanceSession(BaseModel):
    """
    Session model for tracking attendance attempts
    Useful for validating scans and preventing duplicates
    """
    
    class SessionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Validation'
        VALIDATED = 'validated', 'Validated'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'
        FAILED = 'failed', 'Failed'
    
    class ScanMethod(models.TextChoices):
        QR = 'qr', 'QR Code'
        BARCODE = 'barcode', 'Barcode'
        OCR = 'ocr', 'OCR Text'
        MANUAL = 'manual', 'Manual Entry'
        RFID = 'rfid', 'RFID/NFC'
        FACE = 'face', 'Face Recognition'
    
    # Session identification
    session_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Who is scanning
    student = models.ForeignKey(
        'core.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_sessions'
    )
    student_reg_number = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Student registration number from scan"
    )
    
    # What class
    class_obj = models.ForeignKey(
        'core.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_sessions'
    )
    class_code = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Class code from scan"
    )
    
    # Scan details
    scan_method = models.CharField(
        max_length=20,
        choices=ScanMethod.choices,
        default=ScanMethod.QR
    )
    scan_device = models.CharField(
        max_length=100,
        blank=True,
        help_text="Node UUID or camera ID"
    )
    scan_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Physical location of scan"
    )
    
    # Raw scan data
    raw_qr_data = models.TextField(blank=True, help_text="Raw QR code data if applicable")
    raw_ocr_text = models.TextField(blank=True, help_text="Raw OCR extracted text")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    validated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.PENDING,
        db_index=True
    )
    
    # Validation data
    validation_attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    
    # Resulting attendance
    attendance = models.ForeignKey(
        'ClassAttendance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Attendance Session"
        verbose_name_plural = "Attendance Sessions"
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['student_reg_number']),
            models.Index(fields=['class_code']),
            models.Index(fields=['created_at']),
            models.Index(fields=['scan_device']),
        ]
    
    def __str__(self):
        return f"AttendanceSession {self.session_id[:8]} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-set expiry if not set"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if session is still valid"""
        return (self.status == self.SessionStatus.PENDING and 
                self.expires_at > timezone.now())
    
    def is_expired(self):
        """Check if session has expired"""
        return self.expires_at <= timezone.now()
    
    def validate(self):
        """
        Validate the session and create attendance
        Returns dict with result
        """
        self.status = 'validated'
        self.validated_at = timezone.now()
        self.save()
        return True
    
    def mark_validated(self):
        """Mark session as validated"""
        self.status = self.SessionStatus.VALIDATED
        self.validated_at = timezone.now()
        self.save(update_fields=['status', 'validated_at'])
    
    def mark_completed(self, attendance):
        """Mark session as completed with attendance record"""
        self.status = self.SessionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.attendance = attendance
        self.save(update_fields=['status', 'completed_at', 'attendance'])
    
    def mark_failed(self, error_message):
        """Mark session as failed"""
        self.status = self.SessionStatus.FAILED
        self.last_error = error_message
        self.save(update_fields=['status', 'last_error'])
    
    def mark_expired(self):
        """Mark session as expired"""
        if self.is_expired() and self.status == self.SessionStatus.PENDING:
            self.status = self.SessionStatus.EXPIRED
            self.save(update_fields=['status'])
    
    def increment_attempt(self):
        """Increment validation attempt counter"""
        self.validation_attempts += 1
        self.save(update_fields=['validation_attempts'])