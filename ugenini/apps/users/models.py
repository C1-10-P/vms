from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models.person import Person

class User(AbstractUser):
    """
    System User - For authentication ONLY.
    Links to Person for business data.
    """
    # Override email to be unique and required
    email = models.EmailField(unique=True)
    
    # Link to Person (optional - not all users have a Person record)
    person = models.OneToOneField(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_user',
        help_text="Link to business person record (if applicable)"
    )
    institution = models.ForeignKey(
    'core.Institution',
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)
    
    # System-specific fields (NOT business data)
    last_ip_address = models.GenericIPAddressField(null=True, blank=True)
    login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        permissions = [
            # Attendance permissions
            ('can_view_attendance', 'Can view attendance records'),
            ('can_edit_attendance', 'Can edit attendance records'),
            ('can_export_attendance', 'Can export attendance data'),
            
            # Visitor permissions
            ('can_checkin_visitors', 'Can check in visitors'),
            ('can_view_visitors', 'Can view visitor records'),
            ('can_blacklist_visitors', 'Can blacklist visitors'),
            
            # Access control permissions
            ('can_control_gates', 'Can control access gates'),
            ('can_override_access', 'Can override access restrictions'),
            ('can_view_access_logs', 'Can view access logs'),
            
            # Device permissions
            ('can_manage_devices', 'Can manage edge devices'),
            ('can_update_firmware', 'Can update device firmware'),
            
            # Report permissions
            ('can_generate_reports', 'Can generate system reports'),
            ('can_view_analytics', 'Can view analytics dashboard'),
            
            # System permissions
            ('can_manage_users', 'Can manage system users'),
            ('can_view_system_logs', 'Can view system logs'),
        ]
    
    def __str__(self):
        if self.person:
            return f"{self.email} ({self.person.full_name})"
        return self.email
    
    def get_full_name(self):
        """Return person's name if linked, otherwise username"""
        if self.person:
            return self.person.full_name
        return self.username
    
    def is_staff_member(self):
        """Check if user is staff (has staff record)"""
        return getattr(self.person, "person_type", None) == "staff"
    
    def is_lecturer(self):
        """Check if user is a lecturer"""
        return self.is_staff_member() and hasattr(self.person, 'staff') and \
               self.person.staff.staff_category == 'academic'