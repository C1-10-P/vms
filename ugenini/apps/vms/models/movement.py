# apps/visitors/models/movement.py
from django.db import models
from django.utils import timezone
from apps.core.models.base import TimeStampedModel

class VisitorMovement(TimeStampedModel):
    """
    Real-time movement tracking of visitors.
    High-volume table for tracking visitor locations.
    """
    
    class EventType(models.TextChoices):
        ENTER = 'enter', 'Enter Zone'
        EXIT = 'exit', 'Exit Zone'
        PING = 'ping', 'Heartbeat Ping'
        DWELL = 'dwell', 'Dwell Alert'
        ALERT = 'alert', 'Movement Alert'
        PATH = 'path', 'Path Movement'
    
    # Links
    visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.CASCADE,
        related_name='movements',
        db_index=True
    )
    tag = models.ForeignKey(
        'BLETag',
        on_delete=models.SET_NULL,
        null=True,
        related_name='movements'
    )
    visit = models.ForeignKey(
        'VisitorVisit',
        on_delete=models.CASCADE,
        related_name='movements'
    )
    
    # Location
    zone = models.ForeignKey(
    'access.AccessZone',
    on_delete=models.PROTECT,
    related_name='visitor_movements'
    )
    node = models.ForeignKey(
        'firmware.EdgeNode',
        on_delete=models.SET_NULL,
        null=True,
        related_name='detected_movements'
    )
    
    # Movement data
    event_type = models.CharField(
        max_length=10,
        choices=EventType.choices,
        db_index=True
    )
    timestamp = models.DateTimeField(db_index=True)
    
    # Signal strength
    rssi = models.IntegerField(
        null=True,
        blank=True,
        help_text="Received signal strength indicator"
    )
    distance_estimate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated distance in meters"
    )
    
    # Location accuracy
    accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Location accuracy in meters"
    )
    
    # Geolocation (if GPS available)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Dwell time (if event_type is DWELL)
    dwell_seconds = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['visitor', 'timestamp']),
            models.Index(fields=['tag', 'timestamp']),
            models.Index(fields=['zone', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['timestamp']),  # For time-based queries
            # Composite indexes for common queries
            models.Index(fields=['visit', 'zone', 'timestamp']),
            models.Index(fields=['visitor', 'event_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.visitor.person.full_name} - {self.event_type} {self.zone.name} at {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """Auto-set timestamp if not provided"""
        if not self.timestamp:
            self.timestamp = timezone.now()
        super().save(*args, **kwargs)


class MovementPath(TimeStampedModel):
    """
    Pre-computed movement paths for analytics.
    Generated from VisitorMovement records.
    """
    
    class PathType(models.TextChoices):
        WALKING = 'walking', 'Walking'
        RUNNING = 'running', 'Running'
        VEHICLE = 'vehicle', 'Vehicle'
        UNKNOWN = 'unknown', 'Unknown'
    
    visitor = models.ForeignKey(
        'Visitor',
        on_delete=models.CASCADE,
        related_name='paths'
    )
    visit = models.ForeignKey(
        'VisitorVisit',
        on_delete=models.CASCADE,
        related_name='paths'
    )
    
    # Path metadata
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    path_type = models.CharField(
        max_length=20,
        choices=PathType.choices,
        default=PathType.WALKING
    )
    
    # Path data
    zones_visited = models.JSONField(
        default=list,
        help_text="Ordered list of zone IDs visited"
    )
    coordinates = models.JSONField(
        default=list,
        help_text="List of [lat, lng] coordinates"
    )
    
    # Statistics
    total_distance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total distance in meters"
    )
    total_duration = models.DurationField()
    average_speed = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Speed in km/h"
    )
    
    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['visitor', 'start_time']),
            models.Index(fields=['visit', 'start_time']),
            models.Index(fields=['path_type']),
        ]
    
    def __str__(self):
        return f"Path {self.id}: {self.visitor.person.full_name} ({self.start_time.date()})"
    
    @property
    def duration_minutes(self):
        """Get duration in minutes"""
        return self.total_duration.total_seconds() / 60