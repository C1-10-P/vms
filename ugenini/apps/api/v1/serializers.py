from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    full_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    person_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name',
                  'is_active', 'is_staff', 'is_superuser', 'last_login', 'date_joined',
                  'permissions', 'role', 'person_info']
        read_only_fields = ['id', 'last_login', 'date_joined']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_permissions(self, obj):
        from apps.users.permissions import PermissionChecker
        return list(PermissionChecker.get_user_permissions(obj))
    
    def get_role(self, obj):
        from apps.users.permissions import PermissionChecker
        return PermissionChecker.get_user_role(obj)
    
    def get_person_info(self, obj):
        if not hasattr(obj, "person") or obj.person is None:
            return None

        return {
            "id": obj.person.id,
            "name": getattr(obj.person, "full_name", ""),
            "type": getattr(obj.person, "person_type", None),
        }


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Group model"""
    permissions = serializers.StringRelatedField(many=True, read_only=True)
    permission_count = serializers.IntegerField(source='permissions.count', read_only=True)
    user_count = serializers.IntegerField(source='user_set.count', read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'permission_count', 'user_count']


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, validators=[validate_password], write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        return data


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    timestamp = serializers.DateTimeField()
    
    attendance = serializers.DictField(child=serializers.IntegerField())
    visitors = serializers.DictField(child=serializers.IntegerField())
    devices = serializers.DictField(child=serializers.IntegerField())
    security = serializers.DictField(child=serializers.IntegerField())
    
    # Optional detailed fields
    attendance_trend = serializers.ListField(required=False)
    visitor_trend = serializers.ListField(required=False)
    top_zones = serializers.ListField(required=False)
    recent_activity = serializers.ListField(required=False)


class LoginSerializer(serializers.Serializer):
    """Serializer for login request"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response"""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class RealtimeStatsSerializer(serializers.Serializer):
    """Serializer for real-time statistics"""
    current_attendance = serializers.IntegerField()
    active_visitors = serializers.IntegerField()
    online_devices = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results"""
    type = serializers.ChoiceField(choices=['student', 'visitor', 'device', 'person', 'class'])
    id = serializers.IntegerField()
    name = serializers.CharField()
    identifier = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_null=True)
    url = serializers.URLField(required=False, allow_null=True)