from time import timezone

from django.db import models
from apps.core.models.base import BaseModel, SoftDeleteManager

class EdgeNode(BaseModel):
    """
    ESP32-based edge device (camera, BLE scanner, gateway).
    """
    
    class NodeType(models.TextChoices):
        GATEWAY = 'gateway', 'MQTT Gateway'
        CAMERA = 'camera', 'Camera Node (ESP32-CAM)'
        BLE_SCANNER = 'ble_scanner', 'BLE Scanner (ESP32-C3)'
        RFID_READER = 'rfid_reader', 'RFID Reader'
        ACCESS_POINT = 'access_point', 'Access Control Point'
        SENSOR_HUB = 'sensor_hub', 'Sensor Hub'
    
    class NodeStatus(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
        ERROR = 'error', 'Error State'
        BOOTING = 'booting', 'Booting'
        UPDATING = 'updating', 'Updating Firmware'
    
    class PowerSource(models.TextChoices):
        MAINS = 'mains', 'Mains Power'
        BATTERY = 'battery', 'Battery'
        SOLAR = 'solar', 'Solar'
        POE = 'poe', 'Power over Ethernet'
    
    # Identification
    node_uuid = models.CharField(max_length=36, unique=True, db_index=True)
    node_type = models.CharField(max_length=20, choices=NodeType.choices, db_index=True)
    name = models.CharField(max_length=100, blank=True, help_text="Friendly name")
    
    # Hardware
    model = models.CharField(max_length=50, blank=True)
    hardware_version = models.CharField(max_length=20, blank=True)
    firmware_version = models.CharField(max_length=20, blank=True)
    serial_number = models.CharField(max_length=50, unique=True, blank=True)
    
    # Network
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    mac_address = models.CharField(max_length=17, unique=True)
    wifi_ssid = models.CharField(max_length=50, blank=True)
    wifi_rssi = models.IntegerField(null=True, blank=True)
    
    # Location
    institution = models.ForeignKey(
        'core.Institution',
        on_delete=models.CASCADE,
        related_name='edge_nodes'
    )
    college = models.ForeignKey(
        'core.College',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edge_nodes'
    )
    school = models.ForeignKey(
        'core.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edge_nodes'
    )
    department = models.ForeignKey(
        'core.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edge_nodes'
    )
    zone = models.ForeignKey(
        'access.AccessZone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edge_nodes'
    )
    location_description = models.CharField(max_length=255, blank=True)
    
    # Physical location
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Power
    power_source = models.CharField(
        max_length=10,
        choices=PowerSource.choices,
        default=PowerSource.MAINS
    )
    battery_level = models.PositiveSmallIntegerField(null=True, blank=True)
    battery_voltage = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=NodeStatus.choices,
        default=NodeStatus.OFFLINE,
        db_index=True
    )
    last_heartbeat = models.DateTimeField(null=True, blank=True, db_index=True)
    last_boot = models.DateTimeField(null=True, blank=True)
    uptime_seconds = models.PositiveIntegerField(default=0)
    
    # Performance
    cpu_usage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    memory_usage = models.PositiveIntegerField(null=True, blank=True, help_text="Free heap in bytes")
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Configuration
    config_version = models.CharField(max_length=20, default="1.0.0")
    config = models.JSONField(default=dict, help_text="Node-specific configuration")
    
    # Capabilities
    has_camera = models.BooleanField(default=False)
    has_ble = models.BooleanField(default=False)
    has_rfid = models.BooleanField(default=False)
    has_pir = models.BooleanField(default=False)
    has_led = models.BooleanField(default=False)
    has_buzzer = models.BooleanField(default=False)
    
    # Statistics
    total_events = models.PositiveIntegerField(default=0)
    total_errors = models.PositiveIntegerField(default=0)
    last_event_time = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['name', 'node_uuid']
        indexes = [
            models.Index(fields=['node_uuid']),
            models.Index(fields=['mac_address']),
            models.Index(fields=['node_type']),
            models.Index(fields=['status']),
            models.Index(fields=['last_heartbeat']),
            models.Index(fields=['zone']),
            models.Index(fields=['institution']),
        ]
    
    def __str__(self):
        return f"{self.get_node_type_display()} - {self.node_uuid[:8]}"
    
    def update_heartbeat(self, data):
        """Update node heartbeat with latest data"""
        self.last_heartbeat = timezone.now()
        self.status = 'online'
        
        if 'rssi' in data:
            self.wifi_rssi = data['rssi']
        if 'uptime' in data:
            self.uptime_seconds = data['uptime']
        if 'free_heap' in data:
            self.memory_usage = data['free_heap']
        if 'temperature' in data:
            self.temperature = data['temperature']
        if 'battery' in data:
            self.battery_level = data['battery']
        
        self.save(update_fields=[
            'last_heartbeat', 'status', 'wifi_rssi', 'uptime_seconds',
            'memory_usage', 'temperature', 'battery_level'
        ])
    
    def mark_offline(self):
        """Mark node as offline"""
        self.status = 'offline'
        self.save(update_fields=['status'])
    
    def increment_events(self, count=1):
        """Increment event counter"""
        self.total_events += count
        self.last_event_time = timezone.now()
        self.save(update_fields=['total_events', 'last_event_time'])
    
    def increment_errors(self, count=1):
        """Increment error counter"""
        self.total_errors += count
        self.save(update_fields=['total_errors'])
    
    @property
    def is_online(self):
        """Check if node is online"""
        return self.status == 'online'
    
    @property
    def seconds_since_heartbeat(self):
        """Get seconds since last heartbeat"""
        if self.last_heartbeat:
            delta = timezone.now() - self.last_heartbeat
            return delta.total_seconds()
        return None


class NodeCapability(BaseModel):
    """
    Capabilities and features supported by node type.
    """
    
    node_type = models.CharField(max_length=20, choices=EdgeNode.NodeType.choices, unique=True)
    
    # Capabilities
    max_scan_rate_hz = models.PositiveIntegerField(default=10)
    supported_protocols = models.JSONField(default=list, help_text="MQTT, BLE, etc.")
    max_range_meters = models.PositiveIntegerField(default=100)
    power_consumption_ma = models.PositiveIntegerField(default=100)
    
    # Features
    supports_ota = models.BooleanField(default=True)
    supports_encryption = models.BooleanField(default=True)
    supports_battery_monitoring = models.BooleanField(default=False)
    supports_temperature_sensor = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Node Capabilities"
    
    def __str__(self):
        return f"Capabilities for {self.get_node_type_display()}"