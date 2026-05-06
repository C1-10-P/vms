from django.db import models
from apps.core.models.base import BaseModel
from .zone import AccessZone

class AccessPermission(BaseModel):
    """
    Permission rules for zone access.
    Supports role-based and attribute-based access control.
    """
    
    class PersonType(models.TextChoices):
        STUDENT = 'student', 'Student'
        STAFF = 'staff', 'Staff'
        VISITOR = 'visitor', 'Visitor'
        CONTRACTOR = 'contractor', 'Contractor'
        ALUMNI = 'alumni', 'Alumni'
        ALL = 'all', 'All Types'
    
    # Target zone
    zone = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    
    # Who has access (role-based)
    person_type = models.CharField(
        max_length=20,
        choices=PersonType.choices,
        default=PersonType.ALL
    )
    
    # Specific filters
    college = models.ForeignKey(
        'core.College',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Restrict to specific college"
    )
    school = models.ForeignKey(
        'core.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Restrict to specific school"
    )
    department = models.ForeignKey(
        'core.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Restrict to specific department"
    )
    program = models.ForeignKey(
        'core.Program',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Restrict to specific program"
    )
    
    # Attribute-based filters
    year_of_study = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="For students: 1-6"
    )
    staff_category = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="For staff: academic, administrative, etc."
    )
    
    # Specific person override
    specific_person = models.ForeignKey(
        'core.Person',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_permissions'
    )
    
    # Time-based restrictions
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    
    # Day/time restrictions
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)
    
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Access requirements
    requires_2fa = models.BooleanField(default=False)
    requires_escort = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    
    # Priority (higher = overrides lower)
    priority = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['-priority', 'zone']
        indexes = [
            models.Index(fields=['zone', 'person_type']),
            models.Index(fields=['specific_person']),
            models.Index(fields=['valid_from', 'valid_to']),
            models.Index(fields=['department', 'year_of_study']),
        ]
    
    def __str__(self):
        return f"Permission for {self.zone.name}: {self.get_person_type_display()}"
    
    def is_valid_now(self):
        """Check if permission is currently valid"""
        from django.utils import timezone
        now = timezone.now()
        
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        
        # Check day of week
        day_name = now.strftime('%A').lower()
        if not getattr(self, day_name, True):
            return False
        
        # Check time of day
        if self.start_time and self.end_time:
            current_time = now.time()
            if not (self.start_time <= current_time <= self.end_time):
                return False
        
        return True
    
    def check_person_access(self, person):
        """Check if a specific person has access"""
        if self.specific_person and self.specific_person != person:
            return False
        
        if self.person_type != 'all' and person.person_type != self.person_type:
            return False
        
        # Check college/school/department
        if person.person_type == 'student' and hasattr(person, 'student'):
            student = person.student
            if self.college and student.college != self.college:
                return False
            if self.school and student.school != self.school:
                return False
            if self.department and student.department != self.department:
                return False
            if self.year_of_study and student.current_year != self.year_of_study:
                return False
                
        elif person.person_type == 'staff' and hasattr(person, 'staff'):
            staff = person.staff
            if self.department and staff.department != self.department:
                return False
            if self.staff_category and staff.staff_category != self.staff_category:
                return False
        
        return self.is_valid_now()


class ZoneAccessRule(BaseModel):
    """
    Dynamic access rules based on conditions.
    Example: "Lab access only during class hours" or "No access after 8 PM"
    """
    
    class RuleType(models.TextChoices):
        ALLOW = 'allow', 'Allow Access'
        DENY = 'deny', 'Deny Access'
        REQUIRE_2FA = 'require_2fa', 'Require 2FA'
        REQUIRE_ESCORT = 'require_escort', 'Require Escort'
        LOG_ONLY = 'log_only', 'Log Only (No Action)'
    
    zone = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='access_rules'
    )
    
    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RuleType.choices)
    
    # Condition expression (JSON)
    condition = models.JSONField(
        help_text="Condition to evaluate (e.g., {'time_after': '20:00', 'day': 'weekend'})"
    )
    
    # Priority
    priority = models.PositiveSmallIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-priority']
        indexes = [
            models.Index(fields=['zone', 'is_active']),
            models.Index(fields=['rule_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_rule_type_display()}"