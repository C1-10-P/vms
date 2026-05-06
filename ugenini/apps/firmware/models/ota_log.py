from django.db import models
from django.utils import timezone
from apps.core.models.base import BaseModel
from apps.firmware.models import EdgeNode
from apps.firmware.models import FirmwareVersion

class OTASession(BaseModel):
    """
    Over-the-Air update session for a node.
    """
    
    class OTASessionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DOWNLOADING = 'downloading', 'Downloading'
        UPDATING = 'updating', 'Updating'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        ROLLED_BACK = 'rolled_back', 'Rolled Back'
    
    node = models.ForeignKey(
        EdgeNode,
        on_delete=models.CASCADE,
        related_name='ota_sessions'
    )
    
    firmware = models.ForeignKey(
        FirmwareVersion,
        on_delete=models.PROTECT,
        related_name='ota_sessions'
    )
    
    # Session details
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=OTASessionStatus.choices, default=OTASessionStatus.PENDING)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Progress
    progress_percentage = models.PositiveSmallIntegerField(default=0)
    download_size = models.PositiveIntegerField(null=True, blank=True)
    downloaded_bytes = models.PositiveIntegerField(default=0)
    
    # Results
    error_message = models.TextField(blank=True)
    error_code = models.IntegerField(null=True, blank=True)
    
    # Metadata
    initiated_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_ota'
    )
    initiated_via = models.CharField(max_length=20, choices=[('web', 'Web'), ('mqtt', 'MQTT'), ('api', 'API')])
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['node', 'started_at']),
            models.Index(fields=['session_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"OTA {self.session_id[:8]} for {self.node.node_uuid[:8]}"
    
    def update_progress(self, percentage):
        """Update update progress"""
        self.progress_percentage = percentage
        self.save(update_fields=['progress_percentage'])
    
    def complete(self, success=True, error=None):
        """Complete OTA session"""
        self.completed_at = timezone.now()
        self.status = 'success' if success else 'failed'
        if error:
            self.error_message = error
        self.save()
        
        if success:
            self.node.firmware_version = self.firmware.version
            self.node.save()
            self.firmware.increment_success()
        else:
            self.firmware.increment_failure()


class OTAUpdateLog(BaseModel):
    """
    Detailed OTA update logs.
    """
    
    ota_session = models.ForeignKey(
        OTASession,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    log_level = models.CharField(
        max_length=10,
        choices=[('info', 'INFO'), ('warning', 'WARNING'), ('error', 'ERROR'), ('debug', 'DEBUG')]
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['ota_session', 'timestamp']),
            models.Index(fields=['log_level']),
        ]
    
    def __str__(self):
        return f"[{self.log_level}] {self.message[:50]}"