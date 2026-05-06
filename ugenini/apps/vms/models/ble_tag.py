from datetime import timezone
from django.utils import timezone
from django.db import models
from apps.core.models.base import BaseModel, SoftDeleteManager
from apps.core.models.person import Staff

class BLETag(BaseModel):
    """
    BLE Tag hardware for visitor tracking.
    Reusable tags assigned to visitors during their visit.
    """
    
    class TagType(models.TextChoices):
        WEARABLE = 'wearable', 'Wearable Wristband'
        CARD = 'card', 'ID Card'
        STICKER = 'sticker', 'Adhesive Sticker'
        PHONE = 'phone', 'Smartphone App'
    
    class TagStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        ASSIGNED = 'assigned', 'Assigned'
        LOST = 'lost', 'Lost'
        DAMAGED = 'damaged', 'Damaged'
        CHARGING = 'charging', 'Charging'
        RETIRED = 'retired', 'Retired'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
    
    # Hardware identification
    tag_uuid = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        help_text="Unique tag identifier"
    )
    hardware_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="MAC address or hardware serial"
    )
    
    # Tag metadata
    tag_type = models.CharField(
        max_length=20,
        choices=TagType.choices,
        default=TagType.WEARABLE
    )
    manufacturer = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    firmware_version = models.CharField(max_length=20, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=TagStatus.choices,
        default=TagStatus.AVAILABLE,
        db_index=True
    )
    
    # Battery
    battery_level = models.PositiveSmallIntegerField(
        default=100,
        help_text="Battery percentage"
    )
    last_charged = models.DateTimeField(null=True, blank=True)
    battery_threshold = models.PositiveSmallIntegerField(
        default=20,
        help_text="Alert when battery below this level"
    )
    
    # Current assignment
    current_visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tags'
    )
    current_assignment = models.ForeignKey(
        'TagAssignment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    # Location tracking
    last_known_zone = models.ForeignKey(
    'access.AccessZone',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='tags'
    )
    last_ping_time = models.DateTimeField(null=True, blank=True)
    last_rssi = models.IntegerField(null=True, blank=True)
    
    # Statistics
    total_assignments = models.PositiveIntegerField(default=0)
    total_hours_used = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_maintenance = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    
    class Meta:
        ordering = ['tag_uuid']
        indexes = [
            models.Index(fields=['tag_uuid']),
            models.Index(fields=['hardware_id']),
            models.Index(fields=['status']),
            models.Index(fields=['battery_level']),
            models.Index(fields=['last_ping_time']),
        ]
    
    def __str__(self):
       return f"Tag {str(self.tag_uuid)[:8]} ({self.get_tag_type_display()})"
    
    def assign_to_visitor(self, visitor, assigned_by):
        """Assign tag to a visitor"""
        if self.status != 'available':
            raise ValueError(f"Tag is {self.status}, cannot assign")
        
        assignment = TagAssignment.objects.create(
            tag=self,
            visitor=visitor,
            assigned_by=assigned_by,
            assigned_at= timezone.now()
        )
        
        self.status = 'assigned'
        self.current_visitor = visitor
        self.current_assignment = assignment
        self.total_assignments += 1
        self.save()
        
        return assignment
    
    def release(self, released_by):
        """Release tag from visitor"""
        if self.current_assignment:
            self.current_assignment.release(released_by)
        
        self.status = 'available'
        self.current_visitor = None
        self.current_assignment = None
        self.save()
    

    def update_battery(self, level):
        self.battery_level = level
        self.save()
        # Ensure 15 is within this range (15 <= 20)
        if self.battery_level <= 20: 
            self.create_low_battery_alert()

    def create_low_battery_alert(self):
        # 1. Find the current wearer of the tag
        assignment = self.assignments.filter(released_at__isnull=True).first()
        
        if assignment:
            # Import inside the method if needed to avoid circular imports
            from apps.vms.models import VisitorAlert
            
            VisitorAlert.objects.create(
                visitor=assignment.visitor,
                tag=self,  # <--- THIS IS THE MISSING LINK
                alert_type='LOW_BATTERY',
                message=f"Low battery alert for tag {str(self.tag_uuid)[:8]}"
            )
    
    @property
    def is_available(self):
        """Check if tag is available for assignment"""
        return self.status == 'available'
    
    @property
    def battery_ok(self):
        """Check if battery is above threshold"""
        return self.battery_level > self.battery_threshold


class TagAssignment(BaseModel):
    """
    Record of tag assignment to visitor.
    Tracks assignment lifecycle.
    """
    
    class AssignmentStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        LOST = 'lost', 'Tag Lost'
        DAMAGED = 'damaged', 'Tag Damaged'
    
    tag = models.ForeignKey(
        BLETag,
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.PROTECT,
        related_name='tag_assignments'
    )
    
    # Assignment details
    assigned_at = models.DateTimeField(db_index=True)
    assigned_by = models.ForeignKey(
        'core.Staff', 
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        'core.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_tags'
    )
    
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE
    )
    
    # Notes
    assignment_notes = models.TextField(blank=True)
    release_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['assigned_at', 'released_at']),
            models.Index(fields=['status']),
            models.Index(fields=['tag', 'status']),
            models.Index(fields=['visitor', 'status']),
        ]
    
    def __str__(self):
        # Change tag_id to tag_uuid
        short_id = str(self.tag.tag_uuid)[:8]
        return f"Assignment #{self.id}: {short_id} -> {self.visitor.person.full_name}"
    
    def release(self, released_by, notes=""):
        """Release the tag assignment"""
        self.released_at = timezone.now()
        self.released_by = released_by
        self.status = 'completed'
        self.release_notes = notes
        self.save()
        
        # Update tag usage hours
        duration = self.released_at - self.assigned_at
        hours = duration.total_seconds() / 3600
        self.tag.total_hours_used += hours
        self.tag.save()
    
    @property
    def duration(self):
        """Get assignment duration"""
        end_time = self.released_at or timezone.now()
        return end_time - self.assigned_at


class TagActivityLog(BaseModel):
    """
    Detailed log of tag activity for auditing.
    """
    
    class ActivityType(models.TextChoices):
        POWER_ON = 'power_on', 'Power On'
        POWER_OFF = 'power_off', 'Power Off'
        BATTERY_UPDATE = 'battery_update', 'Battery Update'
        MOVEMENT = 'movement', 'Movement Detected'
        ALERT = 'alert', 'Alert Triggered'
        CONFIG_CHANGE = 'config_change', 'Configuration Change'
    
    tag = models.ForeignKey(
        BLETag,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        db_index=True
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Activity data
    data = models.JSONField(default=dict, help_text="Additional activity data")
    
    # Source
    node = models.ForeignKey(
        'firmware.EdgeNode',
        on_delete=models.SET_NULL,
        null=True,
        related_name='tag_activities'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tag', 'timestamp']),
            models.Index(fields=['activity_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.tag.tag_uuid} - {self.activity_type} at {self.timestamp}"