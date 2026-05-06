from rest_framework import serializers
from .models import ClassAttendance, DailyAttendanceSummary, VerificationLog
from apps.core.serializers import StudentSerializer, ClassSerializer


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for ClassAttendance model"""
    student_name = serializers.CharField(source='student.person.full_name', read_only=True)
    student_reg = serializers.CharField(source='student.student_reg_number', read_only=True)
    class_code = serializers.CharField(source='class_obj.class_code', read_only=True)
    course_name = serializers.CharField(source='class_obj.academic_unit.name', read_only=True)
    verification_method_display = serializers.CharField(source='get_verification_method_display', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True, allow_null=True)
    recorded_by_name = serializers.CharField(source='recorded_by.person.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = ClassAttendance
        fields = ['id', 'student', 'student_name', 'student_reg', 'class_obj',
                  'class_code', 'course_name', 'node', 'node_name', 'scan_time',
                  'scan_date', 'verification_method', 'verification_method_display',
                  'verification_status', 'verification_status_display',
                  'confidence_score', 'latitude', 'longitude', 'ip_address',
                  'user_agent', 'raw_data', 'remarks', 'recorded_by', 'recorded_by_name',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'scan_date', 'created_at', 'updated_at']


class AttendanceCreateSerializer(serializers.Serializer):
    """Serializer for creating attendance records"""
    student_id = serializers.CharField(max_length=20, required=True)
    class_code = serializers.CharField(max_length=30, required=True)
    verification_method = serializers.ChoiceField(choices=ClassAttendance.VerificationMethod.choices, default='manual')
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False, allow_null=True)
    node_uuid = serializers.CharField(max_length=36, required=False, allow_null=True)


class DailyAttendanceSummarySerializer(serializers.ModelSerializer):
    """Serializer for DailyAttendanceSummary model"""
    class_code = serializers.CharField(source='class_obj.class_code', read_only=True)
    class_name = serializers.CharField(source='class_obj.academic_unit.name', read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = DailyAttendanceSummary
        fields = ['id', 'class_obj', 'class_code', 'class_name', 'summary_date',
                  'total_students', 'present_count', 'absent_count', 'late_count',
                  'attendance_percentage', 'morning_sessions', 'afternoon_sessions',
                  'evening_sessions', 'generated_at']
        read_only_fields = ['id', 'generated_at']


class VerificationLogSerializer(serializers.ModelSerializer):
    """Serializer for VerificationLog model"""
    student_name = serializers.CharField(source='student.person.full_name', read_only=True, allow_null=True)
    node_name = serializers.CharField(source='node.name', read_only=True, allow_null=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    captured_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VerificationLog
        fields = ['id', 'attendance', 'student', 'student_name', 'node', 'node_name',
                  'event_type', 'event_type_display', 'method', 'method_display',
                  'success', 'failure_reason', 'captured_image', 'captured_image_url',
                  'extracted_data', 'attempt_time', 'processing_time_ms']
        read_only_fields = ['id', 'attempt_time']
    
    def get_captured_image_url(self, obj):
        if obj.captured_image:
            return obj.captured_image.url
        return None


class AttendanceStatsSerializer(serializers.Serializer):
    """Serializer for attendance statistics"""
    total_attendance = serializers.IntegerField()
    today_attendance = serializers.IntegerField()
    this_week_attendance = serializers.IntegerField()
    this_month_attendance = serializers.IntegerField()
    success_rate = serializers.FloatField()
    by_method = serializers.DictField(child=serializers.IntegerField())
    by_hour = serializers.ListField()
    top_students = serializers.ListField()
    top_classes = serializers.ListField()