from rest_framework import serializers
from .models import EdgeNode, NodeHeartbeat, NodeHealth, FirmwareVersion, OTASession, NodeConfiguration


class EdgeNodeSerializer(serializers.ModelSerializer):
    """Serializer for EdgeNode model"""
    node_type_display = serializers.CharField(source='get_node_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    power_source_display = serializers.CharField(source='get_power_source_display', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True, allow_null=True)
    school_name = serializers.CharField(source='school.name', read_only=True, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True, allow_null=True)
    is_online = serializers.BooleanField(read_only=True)
    seconds_since_heartbeat = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = EdgeNode
        fields = ['id', 'uuid', 'node_uuid', 'node_type', 'node_type_display', 'name',
                  'model', 'hardware_version', 'firmware_version', 'serial_number',
                  'ip_address', 'mac_address', 'wifi_ssid', 'wifi_rssi',
                  'institution', 'institution_name', 'college', 'college_name',
                  'school', 'school_name', 'department', 'department_name',
                  'zone', 'zone_name', 'location_description', 'latitude', 'longitude',
                  'power_source', 'power_source_display', 'battery_level', 'battery_voltage',
                  'status', 'status_display', 'last_heartbeat', 'last_boot',
                  'uptime_seconds', 'cpu_usage', 'memory_usage', 'temperature',
                  'config_version', 'config', 'has_camera', 'has_ble', 'has_rfid',
                  'has_pir', 'has_led', 'has_buzzer', 'total_events', 'total_errors',
                  'last_event_time', 'is_online', 'seconds_since_heartbeat',
                  'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'total_events',
                           'total_errors', 'last_event_time', 'is_online',
                           'seconds_since_heartbeat']


class NodeHeartbeatSerializer(serializers.ModelSerializer):
    """Serializer for NodeHeartbeat model"""
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = NodeHeartbeat
        fields = ['id', 'node', 'node_name', 'timestamp', 'rssi', 'ip_address',
                  'uptime_seconds', 'free_heap', 'cpu_freq_mhz', 'temperature',
                  'battery_level', 'battery_voltage', 'is_charging', 'data',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NodeHealthSerializer(serializers.ModelSerializer):
    """Serializer for NodeHealth model"""
    node_name = serializers.CharField(source='node.name', read_only=True)
    health_status_display = serializers.CharField(source='get_health_status_display', read_only=True)
    
    class Meta:
        model = NodeHealth
        fields = ['id', 'node', 'node_name', 'health_status', 'health_status_display',
                  'uptime_percentage_24h', 'avg_rssi_24h', 'avg_cpu_usage_24h',
                  'error_count_24h', 'last_alert', 'alert_count_24h', 'last_updated']
        read_only_fields = ['id', 'last_updated']


class FirmwareVersionSerializer(serializers.ModelSerializer):
    """Serializer for FirmwareVersion model"""
    node_type_display = serializers.CharField(source='get_node_type_display', read_only=True)
    stability_display = serializers.CharField(source='get_stability_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FirmwareVersion
        fields = ['id', 'uuid', 'version', 'node_type', 'node_type_display',
                  'firmware_file', 'file_url', 'file_size', 'md5_hash', 'sha256_hash',
                  'release_date', 'stability', 'stability_display', 'changelog',
                  'min_hardware_version', 'required_config_version', 'rollout_percentage',
                  'is_active', 'total_nodes', 'successful_updates', 'failed_updates',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'total_nodes',
                           'successful_updates', 'failed_updates']
    
    def get_file_url(self, obj):
        if obj.firmware_file:
            return obj.firmware_file.url
        return None


class OTASessionSerializer(serializers.ModelSerializer):
    """Serializer for OTASession model"""
    node_name = serializers.CharField(source='node.name', read_only=True)
    firmware_version = serializers.CharField(source='firmware.version', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    initiated_by_name = serializers.CharField(source='initiated_by.person.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = OTASession
        fields = ['id', 'uuid', 'node', 'node_name', 'firmware', 'firmware_version',
                  'session_id', 'status', 'status_display', 'started_at', 'completed_at',
                  'progress_percentage', 'download_size', 'downloaded_bytes',
                  'error_message', 'error_code', 'initiated_by', 'initiated_by_name',
                  'initiated_via', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class NodeConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for NodeConfiguration model"""
    node_name = serializers.CharField(source='node.name', read_only=True)
    config_dict = serializers.SerializerMethodField()
    
    class Meta:
        model = NodeConfiguration
        fields = ['id', 'uuid', 'node', 'node_name', 'version', 'scan_interval_seconds',
                  'ble_scan_duration', 'ble_scan_window', 'ble_scan_interval',
                  'camera_resolution', 'camera_quality', 'camera_framesize',
                  'mqtt_qos', 'mqtt_retain', 'mqtt_keepalive', 'tls_enabled',
                  'client_certificate', 'deep_sleep_enabled', 'deep_sleep_duration',
                  'log_level', 'custom_settings', 'config_dict', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']
    
    def get_config_dict(self, obj):
        return obj.to_dict()


class DeviceStatsSerializer(serializers.Serializer):
    """Serializer for device statistics"""
    total_devices = serializers.IntegerField()
    online_devices = serializers.IntegerField()
    offline_devices = serializers.IntegerField()
    maintenance_devices = serializers.IntegerField()
    by_type = serializers.ListField()
    low_battery_count = serializers.IntegerField()
    critical_health_count = serializers.IntegerField()
    average_battery = serializers.FloatField()
    average_uptime_days = serializers.FloatField()