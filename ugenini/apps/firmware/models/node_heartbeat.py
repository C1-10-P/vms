from django.db import models
from apps.core.models.base import TimeStampedModel
from apps.firmware.models.edge_node import EdgeNode

class NodeHeartbeat(TimeStampedModel):
    """
    Heartbeat records from edge nodes.
    High-volume table for node monitoring.
    """
    
    node = models.ForeignKey(
        EdgeNode,
        on_delete=models.CASCADE,
        related_name='heartbeats'
    )
    
    timestamp = models.DateTimeField(db_index=True)
    
    # Network metrics
    rssi = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # System metrics
    uptime_seconds = models.PositiveIntegerField()
    free_heap = models.PositiveIntegerField(help_text="Free heap memory in bytes")
    cpu_freq_mhz = models.PositiveIntegerField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Power
    battery_level = models.PositiveSmallIntegerField(null=True, blank=True)
    battery_voltage = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    is_charging = models.BooleanField(default=False)
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['node', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"Heartbeat from {self.node.node_uuid[:8]} at {self.timestamp}"


class NodeHealth(TimeStampedModel):
    """
    Aggregated node health statistics.
    """
    
    class HealthStatus(models.TextChoices):
        HEALTHY = 'healthy', 'Healthy'
        DEGRADED = 'degraded', 'Degraded'
        CRITICAL = 'critical', 'Critical'
        UNKNOWN = 'unknown', 'Unknown'
    
    node = models.OneToOneField(
        EdgeNode,
        on_delete=models.CASCADE,
        related_name='health'
    )
    
    health_status = models.CharField(
        max_length=10,
        choices=HealthStatus.choices,
        default=HealthStatus.UNKNOWN
    )
    
    # 24-hour statistics
    uptime_percentage_24h = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    avg_rssi_24h = models.IntegerField(default=0)
    avg_cpu_usage_24h = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    error_count_24h = models.PositiveIntegerField(default=0)
    
    # Alerts
    last_alert = models.DateTimeField(null=True, blank=True)
    alert_count_24h = models.PositiveIntegerField(default=0)
    
    # Last update
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['health_status']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"Health for {self.node.node_uuid[:8]}: {self.get_health_status_display()}"
    
    def update_status(self):
        """Update health status based on metrics"""
        if self.uptime_percentage_24h < 95:
            self.health_status = 'degraded'
        elif self.error_count_24h > 10:
            self.health_status = 'critical'
        else:
            self.health_status = 'healthy'
        self.save()