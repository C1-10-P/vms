from django.db import models
from apps.core.models.base import BaseModel
from apps.firmware.models import EdgeNode

class FirmwareVersion(BaseModel):
    """
    Firmware versions for edge nodes.
    """
    
    class Stability(models.TextChoices):
        STABLE = 'stable', 'Stable'
        BETA = 'beta', 'Beta'
        ALPHA = 'alpha', 'Alpha'
        DEPRECATED = 'deprecated', 'Deprecated'
    
    version = models.CharField(max_length=20, unique=True)
    node_type = models.CharField(max_length=20, choices=EdgeNode.NodeType.choices)
    
    # File
    firmware_file = models.FileField(upload_to='microcode/')
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    md5_hash = models.CharField(max_length=32)
    sha256_hash = models.CharField(max_length=64)
    
    # Metadata
    release_date = models.DateTimeField()
    stability = models.CharField(max_length=10, choices=Stability.choices, default=Stability.STABLE)
    changelog = models.TextField(blank=True)
    
    # Requirements
    min_hardware_version = models.CharField(max_length=20, blank=True)
    required_config_version = models.CharField(max_length=20, blank=True)
    
    # Rollout
    rollout_percentage = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    total_nodes = models.PositiveIntegerField(default=0)
    successful_updates = models.PositiveIntegerField(default=0)
    failed_updates = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-release_date']
        unique_together = [['node_type', 'version']]
    
    def __str__(self):
        return f"{self.node_type} v{self.version} ({self.get_stability_display()})"
    
    def increment_success(self):
        self.successful_updates += 1
        self.save()
    
    def increment_failure(self):
        self.failed_updates += 1
        self.save()


class FirmwareRelease(BaseModel):
    """
    Scheduled firmware releases/rollouts.
    """
    
    class ReleaseStatus(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    firmware = models.ForeignKey(
        FirmwareVersion,
        on_delete=models.CASCADE,
        related_name='releases'
    )
    
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=ReleaseStatus.choices, default=ReleaseStatus.SCHEDULED)
    
    # Target nodes
    target_nodes = models.ManyToManyField(EdgeNode, related_name='firmware_releases')
    target_groups = models.JSONField(default=list, help_text="Node groups to target")
    
    # Schedule
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Rollout strategy
    batch_size = models.PositiveIntegerField(default=10)
    batch_interval_minutes = models.PositiveIntegerField(default=5)
    current_batch = models.PositiveIntegerField(default=0)
    
    # Results
    total_targets = models.PositiveIntegerField(default=0)
    successful_updates = models.PositiveIntegerField(default=0)
    failed_updates = models.PositiveIntegerField(default=0)
    pending_updates = models.PositiveIntegerField(default=0)
    
    # Rollback
    can_rollback = models.BooleanField(default=True)
    rollback_firmware = models.ForeignKey(
        FirmwareVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rollback_for'
    )
    
    class Meta:
        ordering = ['-scheduled_start']
    
    def __str__(self):
        return f"Release {self.name} - {self.firmware.version}"