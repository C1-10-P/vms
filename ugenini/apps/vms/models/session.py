from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid

from apps.core.models.base import BaseModel
from apps.classroom.models.session import AttendanceSession


class VisitorSession(BaseModel):
    """
    Session model for visitor check-in/check-out process
    Tracks the entire visitor lifecycle from scan to tag assignment
    """
    
    class SessionType(models.TextChoices):
        CHECKIN = 'checkin', 'Check-in'
        CHECKOUT = 'checkout', 'Check-out'
        TAG_ASSIGN = 'tag_assign', 'Tag Assignment'
        TAG_RELEASE = 'tag_release', 'Tag Release'
        OCR_PROCESS = 'ocr_process', 'OCR Processing'
    
    class SessionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        AWAITING_INFO = 'awaiting_info', 'Awaiting Additional Info'
        AWAITING_TAG = 'awaiting_tag', 'Awaiting Tag Assignment'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        FAILED = 'failed', 'Failed'
    
    class IdType(models.TextChoices):
        NATIONAL_ID = 'national_id', 'National ID'
        PASSPORT = 'passport', 'Passport'
        DRIVERS_LICENSE = 'drivers_license', "Driver's License"
        COMPANY_ID = 'company_id', 'Company ID'
        UNKNOWN = 'unknown', 'Unknown'
    
    # Session identification
    session_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=uuid.uuid4,
        editable=False
    )
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        db_index=True
    )
    
    # OCR/Extracted data
    extracted_data = models.JSONField(
        default=dict,
        help_text="Data extracted from ID/QR scan"
    )
    id_type = models.CharField(
        max_length=20,
        choices=IdType.choices,
        default=IdType.UNKNOWN,
        help_text="Type of ID that was scanned"
    )
    raw_ocr_text = models.TextField(blank=True, help_text="Raw OCR extracted text")
    raw_qr_data = models.TextField(blank=True, help_text="Raw QR code data")
    
    # Captured image
    captured_image = models.ImageField(
        upload_to='visitor_sessions/',
        null=True,
        blank=True,
        help_text="Image captured during scan"
    )
    
    # Linked records
    visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    visit = models.ForeignKey(
        'VisitorVisit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    assigned_tag = models.ForeignKey(
        'BLETag',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    
    # Scan details
    scan_method = models.CharField(
        max_length=20,
        choices=AttendanceSession.ScanMethod.choices,
        default='ocr'
    )
    scan_device = models.CharField(max_length=100, blank=True)
    scan_location = models.CharField(max_length=200, blank=True)
    
    # Visitor provided info (for new visitors)
    provided_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Information provided by visitor during check-in"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
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
    notes = models.TextField(blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Visitor Session"
        verbose_name_plural = "Visitor Sessions"
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['visitor']),
            models.Index(fields=['session_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"VisitorSession {self.session_id[:8]} - {self.get_session_type_display()} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-set expiry if not set"""
        if not self.expires_at:
            # Different expiry times based on session type
            if self.session_type in [self.SessionType.CHECKIN, self.SessionType.OCR_PROCESS]:
                self.expires_at = timezone.now() + timedelta(minutes=10)
            elif self.session_type in [self.SessionType.TAG_ASSIGN, self.SessionType.TAG_RELEASE]:
                self.expires_at = timezone.now() + timedelta(minutes=5)
            else:
                self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if session is still valid"""
        return (self.status not in [self.SessionStatus.COMPLETED, 
                                    self.SessionStatus.EXPIRED, 
                                    self.SessionStatus.CANCELLED,
                                    self.SessionStatus.FAILED] and 
                self.expires_at > timezone.now())
    
    def is_expired(self):
        """Check if session has expired"""
        return self.expires_at <= timezone.now()
    
    def complete_checkin(self, visitor, visit=None):
        """
        Complete the check-in process
        Returns dict with result
        """
        from apps.vms.services import VisitorSessionService
        return VisitorSessionService.complete_checkin_session(self.session_id, visitor, visit)
    
    def assign_tag(self, tag):
        """
        Assign a tag to this session
        Returns dict with result
        """
        if not self.is_valid():
            return {'success': False, 'error': 'Session expired'}
        
        self.assigned_tag = tag
        self.status = self.SessionStatus.COMPLETED if self.session_type == self.SessionType.TAG_ASSIGN else self.status
        self.completed_at = timezone.now()
        self.save()
        
        # Actually assign tag to visitor
        if self.visitor:
            tag.assign_to_visitor(self.visitor, None)
        
        return {'success': True, 'tag_uuid': tag.tag_uuid}
    
    def mark_awaiting_info(self):
        """Mark session as awaiting additional visitor info"""
        self.status = self.SessionStatus.AWAITING_INFO
        self.save(update_fields=['status'])
    
    def mark_awaiting_tag(self):
        """Mark session as awaiting tag assignment"""
        self.status = self.SessionStatus.AWAITING_TAG
        self.save(update_fields=['status'])
    
    def mark_completed(self):
        """Mark session as completed"""
        self.status = self.SessionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def mark_failed(self, error_message):
        """Mark session as failed"""
        self.status = self.SessionStatus.FAILED
        self.last_error = error_message
        self.save(update_fields=['status', 'last_error'])
    
    def mark_expired(self):
        """Mark session as expired"""
        if self.is_expired() and self.status not in [self.SessionStatus.COMPLETED, self.SessionStatus.CANCELLED]:
            self.status = self.SessionStatus.EXPIRED
            self.save(update_fields=['status'])
    
    def increment_attempt(self):
        """Increment validation attempt counter"""
        self.validation_attempts += 1
        self.save(update_fields=['validation_attempts'])
    
    def add_provided_info(self, info):
        """Add visitor-provided information"""
        self.provided_info.update(info)
        self.save(update_fields=['provided_info'])
    
    def get_extracted_name(self):
        """Get extracted full name from OCR data"""
        first = self.extracted_data.get('first_name', '')
        last = self.extracted_data.get('last_name', '')
        if first and last:
            return f"{first} {last}"
        return self.extracted_data.get('full_name', 'Unknown')
    
    def get_id_number(self):
        """Get extracted ID number"""
        return self.extracted_data.get('id_number') or self.extracted_data.get('national_id', '')