from time import timezone

from django.db import models
from apps.core.models.base import BaseModel
from apps.access.models.zone import AccessZone

class TwoFactorSession(BaseModel):
    """
    2FA session for access verification.
    """
    
    class SessionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Verification'
        VERIFIED = 'verified', 'Verified'
        EXPIRED = 'expired', 'Expired'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class ChannelType(models.TextChoices):
        SMS = 'sms', 'SMS'
        USSD = 'ussd', 'USSD'
        EMAIL = 'email', 'Email'
        PUSH = 'push', 'Push Notification'
    
    # Session identification
    session_token = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Who
    person = models.ForeignKey(
        'core.Person',
        on_delete=models.CASCADE,
        related_name='two_factor_sessions'
    )
    
    # Where
    zone = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='two_factor_sessions'
    )
    
    # What
    channel = models.CharField(max_length=10, choices=ChannelType.choices, default=ChannelType.USSD)
    otp_code = models.CharField(max_length=10)
    
    # Contact info
    phone_number = models.CharField(max_length=20, blank=True)
    email_address = models.EmailField(blank=True)
    
    # Location verification
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    location_verified = models.BooleanField(default=False)
    distance_from_zone = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Attempts
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    
    status = models.CharField(
        max_length=10,
        choices=SessionStatus.choices,
        default=SessionStatus.PENDING,
        db_index=True
    )
    
    # Metadata
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_token']),
            models.Index(fields=['person', 'created_at']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['otp_code']),
        ]
    
    def __str__(self):
        return f"2FA Session {self.session_token[:8]} for {self.person.full_name}"
    
    def verify(self, code):
        """Verify OTP code"""
        if self.status != 'pending':
            return False, "Session already processed"
        
        if self.expires_at < timezone.now():
            self.status = 'expired'
            self.save()
            return False, "Session expired"
        
        self.attempts += 1
        
        if self.attempts >= self.max_attempts:
            self.status = 'failed'
            self.save()
            return False, "Max attempts exceeded"
        
        if self.otp_code == code:
            self.status = 'verified'
            self.verified_at = timezone.now()
            self.save()
            return True, "Verification successful"
        
        self.save()
        return False, f"Invalid code. {self.max_attempts - self.attempts} attempts remaining"
    
    def is_valid(self):
        """Check if session is still valid"""
        return self.status == 'pending' and self.expires_at > timezone.now()


class TwoFactorLog(BaseModel):
    """
    Log of all 2FA events for auditing.
    """
    
    class EventType(models.TextChoices):
        SENT = 'sent', 'Code Sent'
        VERIFIED = 'verified', 'Code Verified'
        FAILED = 'failed', 'Verification Failed'
        EXPIRED = 'expired', 'Session Expired'
        RESENT = 'resent', 'Code Resent'
    
    session = models.ForeignKey(
        TwoFactorSession,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    event_type = models.CharField(max_length=10, choices=EventType.choices)
    event_time = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Details
    message = models.CharField(max_length=255)
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-event_time']
        indexes = [
            models.Index(fields=['session', 'event_time']),
            models.Index(fields=['event_type', 'event_time']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} for session {self.session.session_token[:8]}"