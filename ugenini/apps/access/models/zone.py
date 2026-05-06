from django.db import models

models.JSONField
from apps.core.models.base import BaseModel, SoftDeleteManager

class AccessZone(BaseModel):
    """
    Physical or logical zone requiring access control.
    Hierarchical structure (Campus -> Building -> Floor -> Room).
    """
    
    class ZoneType(models.TextChoices):
        CAMPUS = 'campus', 'Campus'
        BUILDING = 'building', 'Building'
        FLOOR = 'floor', 'Floor'
        LAB = 'lab', 'Laboratory'
        OFFICE = 'office', 'Office'
        CLASSROOM = 'classroom', 'Classroom'
        LIBRARY = 'library', 'Library'
        HOSPITAL = 'hospital', 'Hospital'
        RESTRICTED = 'restricted', 'Restricted Area'
        RESEARCH = 'research', 'Research Facility'
        SERVER_ROOM = 'server_room', 'Server Room'
        STORAGE = 'storage', 'Storage'
    
    class AccessLevel(models.IntegerChoices):
        PUBLIC = 1, 'Public - Open to all'
        STAFF_ONLY = 2, 'Staff Only'
        RESTRICTED = 3, 'Restricted Access'
        RESEARCH = 4, 'Research Personnel Only'
        AUTHORIZED = 5, 'Authorized Personnel Only'
        EXECUTIVE = 6, 'Executive Level'
    
    # Basic info
    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    zone_type = models.CharField(max_length=20, choices=ZoneType.choices, db_index=True)
    
    # Hierarchy
    parent_zone = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_zones',
        help_text="Parent zone (e.g., Building for Floor)"
    )
    
    # Institution hierarchy (denormalized for performance)
    institution = models.ForeignKey(
        'core.Institution',
        on_delete=models.CASCADE,
        related_name='access_zones'
    )
    college = models.ForeignKey(
        'core.College',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_zones'
    )
    school = models.ForeignKey(
        'core.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_zones'
    )
    department = models.ForeignKey(
        'core.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_zones'
    )
    
    # Access control
    access_level = models.IntegerField(
        choices=AccessLevel.choices,
        default=AccessLevel.PUBLIC
    )
    requires_2fa = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    
    # Physical location
    building = models.CharField(max_length=100, blank=True)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    room_number = models.CharField(max_length=20, blank=True)
    
    # Capacity and occupancy
    capacity = models.PositiveIntegerField(default=0)
    current_occupancy = models.PositiveIntegerField(default=0)
    peak_occupancy = models.PositiveIntegerField(default=0)
    
    # Time restrictions
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    weekend_access = models.BooleanField(default=True)
    holiday_access = models.BooleanField(default=False)
    
    # Geofence
    geofence_coordinates = models.JSONField(
        default=dict,
        blank=True,
        help_text="Polygon coordinates for geofencing"
    )
    geofence_radius = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Radius in meters for circular geofence"
    )
    
    # Security
    requires_escort = models.BooleanField(default=False)
    requires_visa = models.BooleanField(default=False)
    security_level = models.PositiveSmallIntegerField(default=1)
    
    # Metadata
    description = models.TextField(blank=True)
    access_instructions = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=50, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        app_label = 'access'
        ordering = ['institution', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['zone_type']),
            models.Index(fields=['access_level']),
            models.Index(fields=['parent_zone']),
            models.Index(fields=['institution', 'zone_type']),
            models.Index(fields=['building', 'floor']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"
    
    def update_occupancy(self, delta):
        """Update current occupancy"""
        self.current_occupancy += delta
        if self.current_occupancy > self.peak_occupancy:
            self.peak_occupancy = self.current_occupancy
        self.save(update_fields=['current_occupancy', 'peak_occupancy'])
    
    def is_open(self, dt=None):
        """Check if zone is open at given time"""
        from datetime import datetime
        dt = dt or datetime.now()
        
        if dt.weekday() >= 5 and not self.weekend_access:
            return False
        
        if self.open_time and self.close_time:
            current_time = dt.time()
            return self.open_time <= current_time <= self.close_time
        
        return True
    
    def get_hierarchy_path(self):
        """Get full hierarchy path"""
        path = [self.name]
        parent = self.parent_zone
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent_zone
        return " > ".join(path)
    
    @property
    def is_full(self):
        """Check if zone is at capacity"""
        return self.capacity > 0 and self.current_occupancy >= self.capacity
    
    @property
    def occupancy_percentage(self):
        """Get occupancy percentage"""
        if self.capacity == 0:
            return 0
        return (self.current_occupancy / self.capacity) * 100


class ZoneHierarchy(BaseModel):
    """
    Pre-computed zone hierarchy for fast lookups.
    Denormalized table for performance.
    """
    
    ancestor = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='descendants'
    )
    descendant = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='ancestors'
    )
    depth = models.PositiveSmallIntegerField()
    
    class Meta:
        app_label = 'access'
        unique_together = [['ancestor', 'descendant']]
        indexes = [
            models.Index(fields=['ancestor', 'depth']),
            models.Index(fields=['descendant']),
        ]