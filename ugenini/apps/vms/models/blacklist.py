from time import timezone
from django.utils import timezone
from django.db import models
from apps.core.models.base import BaseModel

class BlacklistedVisitor(BaseModel):
    """
    Blacklisted visitors - denied access to institution.
    """
    
    class BlacklistReason(models.TextChoices):
        SECURITY_THREAT = 'security', 'Security Threat'
        MISCONDUCT = 'misconduct', 'Misconduct'
        TRESPASSING = 'trespassing', 'Trespassing'
        THEFT = 'theft', 'Theft'
        VIOLENCE = 'violence', 'Violent Behavior'
        OTHER = 'other', 'Other'
    
    class BlacklistStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        REMOVED = 'removed', 'Removed'
    
    visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.CASCADE,
        related_name='blacklist_entries'
    )
    
    # Blacklist details
    reason_category = models.CharField(
        max_length=20,
        choices=BlacklistReason.choices,
        default=BlacklistReason.OTHER
    )
    reason_description = models.TextField()
    
    # Dates
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=BlacklistStatus.choices,
        default=BlacklistStatus.ACTIVE
    )
    
    # Who blacklisted
    blacklisted_by = models.ForeignKey(
    'core.Staff',
    on_delete=models.CASCADE,
    related_name='vms_blacklisted_visitors'
)
    
    # Removal info
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='removed_blacklist'
    )
    removal_reason = models.TextField(blank=True)
    
    # Evidence
    evidence_notes = models.TextField(blank=True)
    evidence_images = models.JSONField(default=list, help_text="List of image URLs")
    
    class Meta:
        ordering = ['-blacklisted_at']
        indexes = [
            models.Index(fields=['visitor', 'status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['blacklisted_by']),
        ]
    
    def __str__(self):
        return f"{self.visitor.person.full_name} - {self.get_reason_category_display()}"
    
    def is_active(self):
        """Check if blacklist entry is still active"""
        if self.status != 'active':
            return True
        if self.expires_at and self.expires_at < timezone.now():
            self.status = 'expired'
            self.save()
            return False
        return True
    
    def remove(self, removed_by, reason):
        """Remove from blacklist"""
        self.status = 'removed'
        self.removed_at = timezone.now()
        self.removed_by = removed_by
        self.removal_reason = reason
        self.save()


class VisitorAlert(BaseModel):
    """
    Alerts triggered during visitor tracking.
    """
    
    class AlertType(models.TextChoices):
        ZONE_BREACH = 'zone_breach', 'Unauthorized Zone Entry'
        DWELL_TIME = 'dwell_time', 'Excessive Dwell Time'
        TAG_LOST = 'tag_lost', 'Tag Signal Lost'
        LOW_BATTERY = 'low_battery', 'Low Battery'
        MOVEMENT_ANOMALY = 'movement_anomaly', 'Suspicious Movement'
        TIME_EXCEEDED = 'time_exceeded', 'Visit Time Exceeded'
    
    class AlertSeverity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'
    
    class AlertStatus(models.TextChoices):
        NEW = 'new', 'New'
        ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'
    
    visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    tag = models.ForeignKey(
        'BLETag',
        on_delete=models.SET_NULL,
        null=True,
        related_name='alerts'
    )
    visit = models.ForeignKey(
        'VisitorVisit',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    zone = models.ForeignKey(
    'access.AccessZone',
    on_delete=models.SET_NULL,
    null=True,
    related_name='visitor_alerts'
    )
    
    # Alert details
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        db_index=True
    )
    severity = models.CharField(
        max_length=10,
        choices=AlertSeverity.choices,
        default=AlertSeverity.MEDIUM,
        db_index=True
    )
    message = models.TextField()
    
    # Alert data
    data = models.JSONField(default=dict, help_text="Additional alert data")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.NEW,
        db_index=True
    )
    
    # Timestamps
    triggered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Personnel
    acknowledged_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    resolved_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    
    # Resolution
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['visitor', 'triggered_at']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status', 'triggered_at']),
        ]
    
    def __str__(self):
        return f"Zone Breach - {self.visitor.person.full_name}"
    
    def acknowledge(self, staff):
        """Acknowledge alert"""
        self.status = 'acknowledged'
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = staff
        self.save()
    
    def resolve(self, staff, notes=""):
        """Resolve alert"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.resolved_by = staff
        self.resolution_notes = notes
        self.save()