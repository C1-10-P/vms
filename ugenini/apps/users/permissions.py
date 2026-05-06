from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class VMSPermissions:
    """
    Centralized permission definitions for VMS
    """
    
    # Attendance Permissions
    ATTENDANCE_VIEW = 'can_view_attendance'
    ATTENDANCE_CREATE = 'can_create_attendance'
    ATTENDANCE_EDIT = 'can_edit_attendance'
    ATTENDANCE_DELETE = 'can_delete_attendance'
    ATTENDANCE_EXPORT = 'can_export_attendance'
    ATTENDANCE_VERIFY = 'can_verify_attendance'
    
    # Visitor Permissions
    VISITOR_VIEW = 'can_view_visitors'
    VISITOR_CREATE = 'can_create_visitor'
    VISITOR_EDIT = 'can_edit_visitor'
    VISITOR_DELETE = 'can_delete_visitor'
    VISITOR_CHECKIN = 'can_checkin_visitor'
    VISITOR_CHECKOUT = 'can_checkout_visitor'
    VISITOR_BLACKLIST = 'can_blacklist_visitor'
    VISITOR_TRACK = 'can_track_visitor'
    
    # Access Control Permissions
    ACCESS_VIEW_ZONES = 'can_view_zones'
    ACCESS_MANAGE_ZONES = 'can_manage_zones'
    ACCESS_VIEW_LOGS = 'can_view_access_logs'
    ACCESS_GRANT_OVERRIDE = 'can_override_access'
    ACCESS_MANAGE_PERMISSIONS = 'can_manage_permissions'
    ACCESS_2FA_VERIFY = 'can_verify_2fa'
    
    # Device Permissions
    DEVICE_VIEW = 'can_view_devices'
    DEVICE_MANAGE = 'can_manage_devices'
    DEVICE_UPDATE_FIRMWARE = 'can_update_firmware'
    DEVICE_REBOOT = 'can_reboot_devices'
    DEVICE_CONFIGURE = 'can_configure_devices'
    
    # Report Permissions
    REPORT_VIEW = 'can_view_reports'
    REPORT_GENERATE = 'can_generate_reports'
    REPORT_EXPORT = 'can_export_reports'
    REPORT_SCHEDULE = 'can_schedule_reports'
    
    # System Permissions
    SYSTEM_VIEW_LOGS = 'can_view_system_logs'
    SYSTEM_MANAGE_USERS = 'can_manage_users'
    SYSTEM_VIEW_HEALTH = 'can_view_system_health'
    SYSTEM_BACKUP = 'can_backup_system'
    
    @classmethod
    def get_all_permissions(cls):
        """Get all permission codenames"""
        return [getattr(cls, attr) for attr in dir(cls) 
                if not attr.startswith('_') and attr.isupper()]
    
    @classmethod
    def get_permission_groupings(cls):
        """Get permissions grouped by category"""
        return {
            'attendance': [
                cls.ATTENDANCE_VIEW,
                cls.ATTENDANCE_CREATE,
                cls.ATTENDANCE_EDIT,
                cls.ATTENDANCE_DELETE,
                cls.ATTENDANCE_EXPORT,
                cls.ATTENDANCE_VERIFY,
            ],
            'visitors': [
                cls.VISITOR_VIEW,
                cls.VISITOR_CREATE,
                cls.VISITOR_EDIT,
                cls.VISITOR_DELETE,
                cls.VISITOR_CHECKIN,
                cls.VISITOR_CHECKOUT,
                cls.VISITOR_BLACKLIST,
                cls.VISITOR_TRACK,
            ],
            'access': [
                cls.ACCESS_VIEW_ZONES,
                cls.ACCESS_MANAGE_ZONES,
                cls.ACCESS_VIEW_LOGS,
                cls.ACCESS_GRANT_OVERRIDE,
                cls.ACCESS_MANAGE_PERMISSIONS,
                cls.ACCESS_2FA_VERIFY,
            ],
            'devices': [
                cls.DEVICE_VIEW,
                cls.DEVICE_MANAGE,
                cls.DEVICE_UPDATE_FIRMWARE,
                cls.DEVICE_REBOOT,
                cls.DEVICE_CONFIGURE,
            ],
            'reports': [
                cls.REPORT_VIEW,
                cls.REPORT_GENERATE,
                cls.REPORT_EXPORT,
                cls.REPORT_SCHEDULE,
            ],
            'system': [
                cls.SYSTEM_VIEW_LOGS,
                cls.SYSTEM_MANAGE_USERS,
                cls.SYSTEM_VIEW_HEALTH,
                cls.SYSTEM_BACKUP,
            ],
        }


class RoleGroups:
    """
    Predefined role groups with associated permissions
    """
    
    ROLES = {
        'super_admin': {
            'name': 'Super Administrator',
            'permissions': 'all',  # All permissions
            'description': 'Full system access'
        },
        'admin': {
            'name': 'Administrator',
            'permissions': [
                VMSPermissions.ATTENDANCE_VIEW,
                VMSPermissions.ATTENDANCE_EXPORT,
                VMSPermissions.VISITOR_VIEW,
                VMSPermissions.VISITOR_CHECKIN,
                VMSPermissions.VISITOR_CHECKOUT,
                VMSPermissions.ACCESS_VIEW_ZONES,
                VMSPermissions.ACCESS_VIEW_LOGS,
                VMSPermissions.DEVICE_VIEW,
                VMSPermissions.REPORT_VIEW,
                VMSPermissions.REPORT_GENERATE,
                VMSPermissions.SYSTEM_VIEW_HEALTH,
            ],
            'description': 'Day-to-day system administrator'
        },
        'security': {
            'name': 'Security Personnel',
            'permissions': [
                VMSPermissions.VISITOR_VIEW,
                VMSPermissions.VISITOR_CHECKIN,
                VMSPermissions.VISITOR_CHECKOUT,
                VMSPermissions.VISITOR_BLACKLIST,
                VMSPermissions.VISITOR_TRACK,
                VMSPermissions.ACCESS_VIEW_ZONES,
                VMSPermissions.ACCESS_VIEW_LOGS,
                VMSPermissions.ACCESS_GRANT_OVERRIDE,
                VMSPermissions.ACCESS_2FA_VERIFY,
                VMSPermissions.DEVICE_VIEW,
            ],
            'description': 'Security personnel with visitor and access management'
        },
        'lecturer': {
            'name': 'Lecturer',
            'permissions': [
                VMSPermissions.ATTENDANCE_VIEW,
                VMSPermissions.ATTENDANCE_CREATE,
                VMSPermissions.ATTENDANCE_EDIT,
                VMSPermissions.ATTENDANCE_EXPORT,
                VMSPermissions.ATTENDANCE_VERIFY,
                VMSPermissions.REPORT_VIEW,
                VMSPermissions.REPORT_GENERATE,
            ],
            'description': 'Teaching staff with attendance management'
        },
        'hod': {
            'name': 'Head of Department',
            'permissions': [
                VMSPermissions.ATTENDANCE_VIEW,
                VMSPermissions.ATTENDANCE_EXPORT,
                VMSPermissions.VISITOR_VIEW,
                VMSPermissions.ACCESS_VIEW_ZONES,
                VMSPermissions.ACCESS_VIEW_LOGS,
                VMSPermissions.DEVICE_VIEW,
                VMSPermissions.REPORT_VIEW,
                VMSPermissions.REPORT_GENERATE,
                VMSPermissions.REPORT_EXPORT,
            ],
            'description': 'Department head with reporting access'
        },
        'viewer': {
            'name': 'Viewer',
            'permissions': [
                VMSPermissions.ATTENDANCE_VIEW,
                VMSPermissions.VISITOR_VIEW,
                VMSPermissions.ACCESS_VIEW_LOGS,
                VMSPermissions.DEVICE_VIEW,
                VMSPermissions.REPORT_VIEW,
            ],
            'description': 'Read-only access'
        },
    }
    
    @classmethod
    def create_default_groups(cls):
        """Create default groups and assign permissions"""
        from django.contrib.auth.models import Group
        from django.contrib.auth.models import Permission
        
        for role_key, role_data in cls.ROLES.items():
            group, created = Group.objects.get_or_create(name=role_key)
            group.name = role_key
            group.save()
            
            if role_data['permissions'] == 'all':
                # Give all permissions
                permissions = Permission.objects.all()
                group.permissions.set(permissions)
            else:
                # Give specific permissions
                permissions = Permission.objects.filter(
                    codename__in=role_data['permissions']
                )
                group.permissions.set(permissions)
            
            print(f"Group '{role_key}' configured with {group.permissions.count()} permissions")


class PermissionChecker:
    """
    Utility class for checking permissions
    """
    
    @staticmethod
    def has_permission(user, permission_codename):
        """Check if user has specific permission"""
        if not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        return user.has_perm(f'users.{permission_codename}')
    
    @staticmethod
    def has_any_permission(user, permissions_list):
        """Check if user has any of the listed permissions"""
        return any(PermissionChecker.has_permission(user, perm) 
                  for perm in permissions_list)
    
    @staticmethod
    def has_all_permissions(user, permissions_list):
        """Check if user has all listed permissions"""
        return all(PermissionChecker.has_permission(user, perm) 
                  for perm in permissions_list)
    
    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for a user"""
        if user.is_superuser:
            return set(VMSPermissions.get_all_permissions())
        
        permissions = set()
        for group in user.groups.all():
            for perm in group.permissions.all():
                permissions.add(perm.codename)
        
        # Add user-specific permissions
        for perm in user.user_permissions.all():
            permissions.add(perm.codename)
        
        return permissions
    
    @staticmethod
    def get_user_role(user):
        """Get primary role of user"""
        if user.is_superuser:
            return 'super_admin'
        
        groups = user.groups.all()
        if groups.exists():
            return groups.first().name
        
        return None