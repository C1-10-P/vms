from django.db import models
from apps.core.models.base import TimeStampedModel
from apps.access.models.zone import AccessZone

class AccessLog(TimeStampedModel):
    """
    Detailed access attempt logs for security auditing.
    """
    
    class AccessResult(models.TextChoices):
        GRANTED = 'granted', 'Access Granted'
        DENIED = 'denied', 'Access Denied'
        TIMEOUT = 'timeout', '2FA Timeout'
        FAILED = 'failed', 'Verification Failed'
        BLOCKED = 'blocked', 'Access Blocked'
        ESCALATED = 'escalated', 'Escalated for Review'
    
    class VerificationMethod(models.TextChoices):
        TAG = 'tag', 'BLE Tag'
        RFID = 'rfid', 'RFID Card'
        FACE = 'face', 'Face Recognition'
        QR = 'qr', 'QR Code'
        USSD = 'ussd', 'USSD/2FA'
        MANUAL = 'manual', 'Manual Override'
        BIOMETRIC = 'biometric', 'Biometric'
    
    # Who
    person = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        related_name='access_logs',
        db_index=True
    )
    person_type = models.CharField(max_length=20, db_index=True)
    
    # Where
    zone = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='access_logs',
        null=True, 
        blank=True,
        db_index=True

    )
    
    # How
    verification_method = models.CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        db_index=True
    )
    node = models.ForeignKey(
        'firmware.EdgeNode',
        on_delete=models.SET_NULL,
        null=True,
        related_name='access_logs'
    )
    
    # Result
    result = models.CharField(
        max_length=20,
        choices=AccessResult.choices,
        db_index=True
    )
    reason = models.CharField(max_length=255, blank=True)
    
    # Timing
    access_time = models.DateTimeField(db_index=True)
    response_time_ms = models.PositiveIntegerField(help_text="Response time in milliseconds")
    
    # Location verification
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    location_verified = models.BooleanField(default=False)
    distance_from_zone = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # 2FA
    two_factor_used = models.BooleanField(default=False)
    two_factor_verified = models.BooleanField(default=False)
    
    # Authentication data
    credential_used = models.CharField(max_length=100, blank=True)
    credential_data = models.JSONField(default=dict, blank=True)
    
    # Audit
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-access_time']
        indexes = [
            models.Index(fields=['access_time']),
            models.Index(fields=['person', 'access_time']),
            models.Index(fields=['zone', 'access_time']),
            models.Index(fields=['result', 'access_time']),
            models.Index(fields=['session_id']),
            # Composite indexes for common queries
            models.Index(fields=['person', 'zone', 'access_time']),
            models.Index(fields=['zone', 'result', 'access_time']),
        ]
    
    def __str__(self):
        person_name = self.person.full_name if self.person else "Unknown"
        return f"{person_name} - {self.zone.name} - {self.result} at {self.access_time}"


class AccessAttempt(TimeStampedModel):
    """
    Failed access attempts for security monitoring.
    Used for detecting brute force or suspicious activity.
    """
    
    class AttemptType(models.TextChoices):
        TAG_SCAN = 'tag_scan', 'Tag Scan'
        FACE_SCAN = 'face_scan', 'Face Scan'
        RFID_SCAN = 'rfid_scan', 'RFID Scan'
        MANUAL_ENTRY = 'manual_entry', 'Manual Entry'
        API_REQUEST = 'api_request', 'API Request'
    
    # Attempt details
    attempt_type = models.CharField(max_length=20, choices=AttemptType.choices)
    credential = models.CharField(max_length=100, blank=True, help_text="Credential used")
    
    # Source
    node = models.ForeignKey(
        'firmware.EdgeNode',
        on_delete=models.SET_NULL,
        null=True,
        related_name='failed_attempts'
    )
    zone = models.ForeignKey(
        AccessZone,
        on_delete=models.SET_NULL,
        null=True,
        related_name='failed_attempts'
    )
    
    # Failure reason
    failure_reason = models.CharField(max_length=255)
    
    # Attempt data
    attempt_time = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Person if identified
    person = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='failed_attempts'
    )
    
    class Meta:
        ordering = ['-attempt_time']
        indexes = [
            models.Index(fields=['attempt_time']),
            models.Index(fields=['credential']),
            models.Index(fields=['node', 'attempt_time']),
            models.Index(fields=['person', 'attempt_time']),
        ]
    
    def __str__(self):
        return f"Failed {self.attempt_type} at {self.attempt_time}"