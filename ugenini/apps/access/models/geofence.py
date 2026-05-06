from django.db import models
from apps.core.models.base import BaseModel
from .zone import AccessZone

class GeofenceBoundary(BaseModel):
    """
    Geofence boundaries for zones.
    Supports polygons, circles, and points with radius.
    """
    
    class BoundaryType(models.TextChoices):
        POLYGON = 'polygon', 'Polygon'
        CIRCLE = 'circle', 'Circle'
        POINT = 'point', 'Point'
        PATH = 'path', 'Path/Route'
    
    zone = models.OneToOneField(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='geofence'
    )
    
    boundary_type = models.CharField(
        max_length=10,
        choices=BoundaryType.choices,
        default=BoundaryType.POLYGON
    )
    
    # Coordinates storage
    coordinates = models.JSONField(
        help_text="For polygon: list of [lat,lng]; For circle: [center_lat, center_lng, radius]"
    )
    
    # For point/radius
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    radius_meters = models.PositiveIntegerField(null=True, blank=True)
    
    # Precision
    accuracy_threshold = models.PositiveIntegerField(
        default=10,
        help_text="GPS accuracy threshold in meters"
    )
    
    # Validation
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-id']  
        indexes = [
            
            models.Index(fields=['zone']),
            models.Index(fields=['boundary_type']),
        ]
    
    def __str__(self):
        return f"Geofence for {self.zone.name} ({self.get_boundary_type_display()})"
    
    def contains_point(self, lat, lng):
        """
        Check if a point is inside the geofence.
        Simplified - in production use GIS libraries.
        """
        if self.boundary_type == 'circle':
            from math import radians, sin, cos, sqrt, atan2
            # Haversine formula
            R = 6371000  # Earth radius in meters
            lat1, lon1 = radians(self.latitude), radians(self.longitude)
            lat2, lon2 = radians(lat), radians(lng)
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            return distance <= self.radius_meters
        
        # For polygon, would need point-in-polygon algorithm
        # For simplicity, return True if within bounding box
        return True  # Implement actual logic in production
    
    def get_geojson(self):
        """Return geofence as GeoJSON"""
        if self.boundary_type == 'polygon':
            return {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [self.coordinates]
                },
                "properties": {
                    "zone_id": self.zone.id,
                    "zone_name": self.zone.name
                }
            }
        return None


class GeofenceEvent(BaseModel):
    """
    Events triggered by geofence boundaries.
    """
    
    class EventType(models.TextChoices):
        ENTER = 'enter', 'Entered Geofence'
        EXIT = 'exit', 'Exited Geofence'
        DWELL = 'dwell', 'Dwell Time Exceeded'
        BREACH = 'breach', 'Geofence Breach'
    
    person = models.ForeignKey(
        'core.Person',
        on_delete=models.CASCADE,
        related_name='geofence_events'
    )
    zone = models.ForeignKey(
        AccessZone,
        on_delete=models.CASCADE,
        related_name='geofence_events'
    )
    
    event_type = models.CharField(max_length=10, choices=EventType.choices)
    event_time = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.PositiveIntegerField(help_text="GPS accuracy in meters")
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-event_time']
        indexes = [
            models.Index(fields=['person', 'event_time']),
            models.Index(fields=['zone', 'event_time']),
            models.Index(fields=['event_type', 'event_time']),
        ]
    
    def __str__(self):
        return f"{self.person.full_name} {self.get_event_type_display()} {self.zone.name}"