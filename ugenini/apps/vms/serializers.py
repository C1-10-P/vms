from rest_framework import serializers

from .models import Visitor, BLETag, VisitorVisit, VisitorMovement, VisitorAlert, BlacklistedVisitor
from apps.core.models import Person
from apps.core.serializers import PersonSerializer


class VisitorSerializer(serializers.ModelSerializer):
    """Serializer for Visitor model"""
    person = PersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(person_type='visitor'),
        source='person',
        write_only=True
    )
    host_name = serializers.CharField(source='host_person.full_name', read_only=True, allow_null=True)
    host_department_name = serializers.CharField(source='host_department.name', read_only=True, allow_null=True)
    purpose_display = serializers.CharField(source='get_purpose_display', read_only=True)
    id_type_display = serializers.CharField(source='get_id_type_display', read_only=True)
    is_blacklisted = serializers.BooleanField(read_only=True)
    is_on_campus = serializers.BooleanField(read_only=True)
    status = serializers.BooleanField(read_only=True)
    current_visit_id = serializers.IntegerField(source='current_visit.id', read_only=True, allow_null=True)
    
    class Meta:
        model = Visitor
        fields = ['id', 'person', 'person_id', 'institution', 'purpose',
                  'purpose_display', 'purpose_description', 'host_person', 'host_name',
                  'host_department', 'host_department_name', 'id_type', 'id_type_display',
                  'id_number', 'id_verified', 'id_verified_by', 'id_verified_at',
                  'id_photo', 'vehicle_registration', 'vehicle_make', 'vehicle_model',
                  'vehicle_color', 'organization', 'organization_phone', 'organization_email',
                  'total_visits', 'last_visit', 'average_visit_duration', 'is_verified',
                  'verified_at', 'is_blacklisted', 'is_on_campus', 'current_visit_id',
                  'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_visits',
                           'last_visit', 'is_blacklisted', 'is_on_campus']


class VisitorCheckinSerializer(serializers.Serializer):
    """Serializer for visitor check-in"""
    first_name = serializers.CharField(max_length=50, required=True)
    last_name = serializers.CharField(max_length=50, required=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=True)
    national_id = serializers.CharField(max_length=20, required=True)
    organization = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.ChoiceField(choices=Visitor.VisitPurpose.choices, required=True)
    purpose_description = serializers.CharField(required=False, allow_blank=True)
    host_email = serializers.EmailField(required=False, allow_blank=True)
    host_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    vehicle_registration = serializers.CharField(max_length=20, required=False, allow_blank=True)


class VisitorCheckoutSerializer(serializers.Serializer):
    """Serializer for visitor check-out"""
    tag_uuid = serializers.CharField(max_length=36, required=True)
    checkout_notes = serializers.CharField(required=False, allow_blank=True)


class BLETagSerializer(serializers.ModelSerializer):
    """Serializer for BLETag model"""
    tag_type_display = serializers.CharField(source='get_tag_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_visitor_name = serializers.CharField(source='current_visitor.person.full_name', read_only=True, allow_null=True)
    current_visitor_id = serializers.IntegerField(source='current_visitor.id', read_only=True, allow_null=True)
    last_zone_name = serializers.CharField(source='last_known_zone.name', read_only=True, allow_null=True)
    battery_ok = serializers.BooleanField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = BLETag
        fields = ['id', 'uuid', 'tag_uuid', 'hardware_id', 'tag_type', 'tag_type_display',
                  'manufacturer', 'model', 'firmware_version', 'status', 'status_display',
                  'battery_level', 'battery_threshold', 'battery_ok', 'last_charged',
                  'current_visitor', 'current_visitor_name', 'current_visitor_id',
                  'current_assignment', 'last_known_zone', 'last_zone_name',
                  'last_ping_time', 'last_rssi', 'total_assignments', 'total_hours_used',
                  'is_available', 'last_maintenance', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'total_assignments', 'total_hours_used']


class VisitorVisitSerializer(serializers.ModelSerializer):
    """Serializer for VisitorVisit model"""
    visitor_name = serializers.CharField(source='visitor.person.full_name', read_only=True)
    visitor_id_number = serializers.CharField(source='visitor.id_number', read_only=True)
    assigned_tag_uuid = serializers.CharField(source='assigned_tag.tag_uuid', read_only=True, allow_null=True)
    checked_in_by_name = serializers.CharField(source='checked_in_by.person.full_name', read_only=True, allow_null=True)
    checked_out_by_name = serializers.CharField(source='checked_out_by.person.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = VisitorVisit
        fields = ['id', 'uuid', 'visitor', 'visitor_name', 'visitor_id_number',
                  'assigned_tag', 'assigned_tag_uuid', 'check_in_time', 'check_out_time',
                  'check_in_node', 'check_out_node', 'checked_in_by', 'checked_in_by_name',
                  'checked_out_by', 'checked_out_by_name', 'status', 'status_display',
                  'check_in_notes', 'check_out_notes', 'total_movements', 'zones_visited',
                  'duration_hours', 'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']
    
    def get_duration_hours(self, obj):
        if obj.check_out_time:
            duration = obj.check_out_time - obj.check_in_time
            return round(duration.total_seconds() / 3600, 2)
        return None


class VisitorMovementSerializer(serializers.ModelSerializer):
    """Serializer for VisitorMovement model"""
    visitor_name = serializers.CharField(source='visitor.person.full_name', read_only=True)
    tag_uuid = serializers.CharField(source='tag.tag_uuid', read_only=True, allow_null=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True, allow_null=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = VisitorMovement
        fields = ['id', 'visitor', 'visitor_name', 'tag', 'tag_uuid', 'visit',
                  'zone', 'zone_name', 'node', 'node_name', 'event_type',
                  'event_type_display', 'timestamp', 'rssi', 'distance_estimate',
                  'accuracy', 'latitude', 'longitude', 'dwell_seconds',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VisitorAlertSerializer(serializers.ModelSerializer):
    """Serializer for VisitorAlert model"""
    visitor_name = serializers.CharField(source='visitor.person.full_name', read_only=True)
    tag_uuid = serializers.CharField(source='tag.tag_uuid', read_only=True, allow_null=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True, allow_null=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = VisitorAlert
        fields = ['id', 'uuid', 'visitor', 'visitor_name', 'tag', 'tag_uuid',
                  'visit', 'zone', 'zone_name', 'alert_type', 'alert_type_display',
                  'severity', 'severity_display', 'message', 'data', 'status',
                  'status_display', 'triggered_at', 'acknowledged_at', 'resolved_at',
                  'acknowledged_by', 'resolved_by', 'resolution_notes',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class VisitorStatsSerializer(serializers.Serializer):
    """Serializer for visitor statistics"""
    total_visitors = serializers.IntegerField()
    active_visitors = serializers.IntegerField()
    total_visits_today = serializers.IntegerField()
    total_visits_this_week = serializers.IntegerField()
    total_visits_this_month = serializers.IntegerField()
    average_visit_duration = serializers.FloatField()
    popular_purposes = serializers.DictField(child=serializers.IntegerField())
    popular_organizations = serializers.ListField()
    hourly_distribution = serializers.ListField()