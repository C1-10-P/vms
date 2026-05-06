from rest_framework import serializers
from apps.access.models.zone import AccessZone
from apps.access.models.permission import AccessPermission
from apps.access.models.two_factor import TwoFactorSession
from apps.access.models.log import AccessLog
from apps.access.models.geofence import GeofenceBoundary
from apps.core.serializers import PersonSerializer


class AccessZoneSerializer(serializers.ModelSerializer):
    """Serializer for AccessZone model"""
    zone_type_display = serializers.CharField(source='get_zone_type_display', read_only=True)
    access_level_display = serializers.CharField(source='get_access_level_display', read_only=True)
    parent_zone_name = serializers.CharField(source='parent_zone.name', read_only=True, allow_null=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True, allow_null=True)
    school_name = serializers.CharField(source='school.name', read_only=True, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    occupancy_percentage = serializers.FloatField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    full_hierarchy = serializers.CharField(read_only=True)
    
    class Meta:
        model = AccessZone
        fields = ['id', 'uuid', 'name', 'code', 'zone_type', 'zone_type_display',
                  'parent_zone', 'parent_zone_name', 'institution', 'institution_name',
                  'college', 'college_name', 'school', 'school_name', 'department',
                  'department_name', 'access_level', 'access_level_display',
                  'requires_2fa', 'requires_approval', 'building', 'floor',
                  'room_number', 'capacity', 'current_occupancy', 'peak_occupancy',
                  'occupancy_percentage', 'is_full', 'open_time', 'close_time',
                  'weekend_access', 'holiday_access', 'is_open', 'geofence_coordinates',
                  'geofence_radius', 'requires_escort', 'requires_visa',
                  'security_level', 'description', 'access_instructions',
                  'emergency_contact', 'full_hierarchy', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'current_occupancy',
                           'peak_occupancy', 'occupancy_percentage', 'is_full', 'is_open']


class AccessPermissionSerializer(serializers.ModelSerializer):
    """Serializer for AccessPermission model"""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    person_type_display = serializers.CharField(source='get_person_type_display', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True, allow_null=True)
    school_name = serializers.CharField(source='school.name', read_only=True, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    program_name = serializers.CharField(source='program.name', read_only=True, allow_null=True)
    specific_person_name = serializers.CharField(source='specific_person.full_name', read_only=True, allow_null=True)
    is_valid_now = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AccessPermission
        fields = ['id', 'uuid', 'zone', 'zone_name', 'person_type', 'person_type_display',
                  'college', 'college_name', 'school', 'school_name', 'department',
                  'department_name', 'program', 'program_name', 'year_of_study',
                  'staff_category', 'specific_person', 'specific_person_name',
                  'valid_from', 'valid_to', 'monday', 'tuesday', 'wednesday',
                  'thursday', 'friday', 'saturday', 'sunday', 'start_time',
                  'end_time', 'requires_2fa', 'requires_escort', 'requires_approval',
                  'priority', 'is_valid_now', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'is_valid_now']


class AccessLogSerializer(serializers.ModelSerializer):
    """Serializer for AccessLog model"""
    person_name = serializers.CharField(source='person.full_name', read_only=True, default='Unknown')
    person_type_display = serializers.CharField(source='get_person_type_display', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    verification_method_display = serializers.CharField(source='get_verification_method_display', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True, allow_null=True)
    
    class Meta:
        model = AccessLog
        fields = ['id', 'person', 'person_name', 'person_type', 'person_type_display',
                  'zone', 'zone_name', 'verification_method', 'verification_method_display',
                  'node', 'node_name', 'result', 'result_display', 'reason',
                  'access_time', 'response_time_ms', 'latitude', 'longitude',
                  'location_verified', 'distance_from_zone', 'two_factor_used',
                  'two_factor_verified', 'credential_used', 'credential_data',
                  'ip_address', 'user_agent', 'session_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TwoFactorSessionSerializer(serializers.ModelSerializer):
    """Serializer for TwoFactorSession model"""
    person_name = serializers.CharField(source='person.full_name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TwoFactorSession
        fields = ['id', 'uuid', 'session_token', 'person', 'person_name', 'zone',
                  'zone_name', 'channel', 'channel_display', 'otp_code', 'phone_number',
                  'email_address', 'latitude', 'longitude', 'location_verified',
                  'distance_from_zone', 'created_at', 'expires_at', 'verified_at',
                  'attempts', 'max_attempts', 'status', 'status_display', 'is_valid',
                  'user_agent', 'ip_address']
        read_only_fields = ['id', 'uuid', 'created_at', 'otp_code']


class GeofenceBoundarySerializer(serializers.ModelSerializer):
    """Serializer for GeofenceBoundary model"""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    boundary_type_display = serializers.CharField(source='get_boundary_type_display', read_only=True)
    geojson = serializers.SerializerMethodField()
    
    class Meta:
        model = GeofenceBoundary
        fields = ['id', 'uuid', 'zone', 'zone_name', 'boundary_type',
                  'boundary_type_display', 'coordinates', 'latitude', 'longitude',
                  'radius_meters', 'accuracy_threshold', 'is_active', 'geojson',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']
    
    def get_geojson(self, obj):
        return obj.get_geojson()


class AccessStatsSerializer(serializers.Serializer):
    """Serializer for access statistics"""
    total_attempts = serializers.IntegerField()
    granted = serializers.IntegerField()
    denied = serializers.IntegerField()
    success_rate = serializers.FloatField()
    today_attempts = serializers.IntegerField()
    this_week_attempts = serializers.IntegerField()
    by_zone = serializers.ListField()
    by_hour = serializers.ListField()
    two_factor_usage = serializers.IntegerField()
    top_users = serializers.ListField()