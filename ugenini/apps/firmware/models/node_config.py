from django.db import models
from apps.core.models.base import BaseModel
from apps.firmware.models.edge_node import EdgeNode

class NodeConfiguration(BaseModel):
    """
    Configuration for edge nodes.
    """
    
    node = models.OneToOneField(
        EdgeNode,
        on_delete=models.CASCADE,
        related_name='configuration'
    )
    
    version = models.CharField(max_length=20, default="1.0.0")
    
    # Scan settings
    scan_interval_seconds = models.PositiveIntegerField(default=30)
    ble_scan_duration = models.PositiveIntegerField(default=5, help_text="BLE scan duration in seconds")
    ble_scan_window = models.PositiveIntegerField(default=4, help_text="BLE scan window in seconds")
    ble_scan_interval = models.PositiveIntegerField(default=100, help_text="BLE scan interval in ms")
    
    # Camera settings (if applicable)
    camera_resolution = models.CharField(max_length=20, default="QVGA")
    camera_quality = models.PositiveSmallIntegerField(default=12, help_text="JPEG quality 0-63")
    camera_framesize = models.CharField(max_length=20, default="FRAMESIZE_QVGA")
    
    # MQTT settings
    mqtt_qos = models.PositiveSmallIntegerField(default=1, choices=[(0, '0'), (1, '1'), (2, '2')])
    mqtt_retain = models.BooleanField(default=False)
    mqtt_keepalive = models.PositiveIntegerField(default=60)
    
    # Security
    tls_enabled = models.BooleanField(default=True)
    client_certificate = models.TextField(blank=True)
    
    # Power management
    deep_sleep_enabled = models.BooleanField(default=False)
    deep_sleep_duration = models.PositiveIntegerField(default=300, help_text="Sleep duration in seconds")
    
    # Logging
    log_level = models.CharField(
        max_length=10,
        choices=[('debug', 'DEBUG'), ('info', 'INFO'), ('warn', 'WARN'), ('error', 'ERROR')],
        default='info'
    )
    
    # Custom config
    custom_settings = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['node', 'version']),
        ]
    
    def __str__(self):
        return f"Config v{self.version} for {self.node.node_uuid[:8]}"
    
    def to_dict(self):
        """Convert configuration to dictionary for MQTT"""
        return {
            'version': self.version,
            'scan_interval': self.scan_interval_seconds,
            'ble': {
                'scan_duration': self.ble_scan_duration,
                'scan_window': self.ble_scan_window,
                'scan_interval': self.ble_scan_interval,
            },
            'camera': {
                'resolution': self.camera_resolution,
                'quality': self.camera_quality,
                'framesize': self.camera_framesize,
            } if self.node.has_camera else None,
            'mqtt': {
                'qos': self.mqtt_qos,
                'retain': self.mqtt_retain,
                'keepalive': self.mqtt_keepalive,
            },
            'power': {
                'deep_sleep_enabled': self.deep_sleep_enabled,
                'deep_sleep_duration': self.deep_sleep_duration,
            },
            'log_level': self.log_level,
            **self.custom_settings
        }


class ConfigHistory(BaseModel):
    """
    History of configuration changes for auditing.
    """
    
    node = models.ForeignKey(
        EdgeNode,
        on_delete=models.CASCADE,
        related_name='config_history'
    )
    
    version = models.CharField(max_length=20)
    old_config = models.JSONField()
    new_config = models.JSONField()
    
    changed_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='config_changes'
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    
    change_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['node', 'changed_at']),
            models.Index(fields=['version']),
        ]
    
    def __str__(self):
        return f"Config change for {self.node.node_uuid[:8]} to v{self.version}"