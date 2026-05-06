from django.db import models
from django.utils import timezone
from apps.core.models.base import BaseModel, TimeStampedModel

class Notification(BaseModel):
    """
    System notification for users.
    """
    
    class NotificationType(models.TextChoices):
        ATTENDANCE = 'attendance', 'Attendance'
        VISITOR = 'visitor', 'Visitor'
        ACCESS = 'access', 'Access'
        SYSTEM = 'system', 'System'
        SECURITY = 'security', 'Security'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'
        FAILED = 'failed', 'Failed'
    
    # Recipient
    recipient = models.ForeignKey(
        'core.Person',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification details
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Links
    action_url = models.CharField(max_length=500, blank=True)
    related_object_id = models.CharField(max_length=50, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Expiry
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title[:50]}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()
    
    def is_expired(self):
        """Check if notification is expired"""
        return self.expires_at and self.expires_at < timezone.now()


class SMSLog(TimeStampedModel):
    """
    SMS message log.
    """
    
    class SMSStatus(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
    
    # Recipient
    recipient_number = models.CharField(max_length=20, db_index=True)
    recipient_person = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sms_logs'
    )
    
    # Message
    message = models.TextField()
    message_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Status
    status = models.CharField(max_length=20, choices=SMSStatus.choices, default=SMSStatus.QUEUED)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Provider
    provider = models.CharField(max_length=50, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Cost
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Source
    source = models.CharField(max_length=50, blank=True, help_text="What triggered this SMS")
    
    class Meta:
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['recipient_number', 'queued_at']),
            models.Index(fields=['status']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"SMS to {self.recipient_number}: {self.status}"


class EmailLog(TimeStampedModel):
    """
    Email message log.
    """
    
    class EmailStatus(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        OPENED = 'opened', 'Opened'
        CLICKED = 'clicked', 'Clicked'
        FAILED = 'failed', 'Failed'
    
    # Recipient
    recipient_email = models.EmailField(db_index=True)
    recipient_person = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        related_name='email_logs'
    )
    
    # Email details
    subject = models.CharField(max_length=200)
    body_text = models.TextField()
    body_html = models.TextField(blank=True)
    
    # Headers
    from_email = models.EmailField()
    reply_to = models.EmailField(blank=True)
    cc = models.JSONField(default=list, blank=True)
    bcc = models.JSONField(default=list, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=EmailStatus.choices, default=EmailStatus.QUEUED)
    message_id = models.CharField(max_length=200, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    click_url = models.CharField(max_length=500, blank=True)
    
    # Provider
    provider = models.CharField(max_length=50, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['recipient_email', 'queued_at']),
            models.Index(fields=['status']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"Email to {self.recipient_email}: {self.subject[:50]}"


class USSDSession(BaseModel):
    """
    USSD session for 2FA and visitor interactions.
    """
    
    class SessionStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class SessionType(models.TextChoices):
        TWO_FACTOR = '2fa', 'Two-Factor Authentication'
        VISITOR_CHECKIN = 'checkin', 'Visitor Check-in'
        VISITOR_CHECKOUT = 'checkout', 'Visitor Check-out'
        ALERT_RESPONSE = 'alert', 'Alert Response'
    
    # Session identification
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    
    # Session details
    session_type = models.CharField(max_length=20, choices=SessionType.choices)
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.ACTIVE)
    
    # Related data
    person = models.ForeignKey(
        'core.Person',
        on_delete=models.SET_NULL,
        null=True,
        related_name='ussd_sessions'
    )
    two_factor_session = models.ForeignKey(
    'access.TwoFactorSession',
    on_delete=models.SET_NULL,
    null=True,
    related_name='ussd_session'
    )
    
    # Menu state
    current_menu = models.CharField(max_length=50, default="main")
    user_input = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Logs
    interaction_log = models.JSONField(default=list, help_text="Log of USSD interactions")
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"USSD Session {self.session_id} - {self.get_session_type_display()}"
    
    def add_interaction(self, user_input, response):
        """Log USSD interaction"""
        self.interaction_log.append({
            'timestamp': timezone.now().isoformat(),
            'user_input': user_input,
            'response': response
        })
        self.last_activity = timezone.now()
        self.save()