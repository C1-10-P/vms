import math
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.core.cache import cache
import numpy as np

logger = logging.getLogger(__name__)


class VisitorMovementService:
    """
    Service for tracking and analyzing visitor movements
    """
    
    # RSSI to distance conversion constants
    RSSI_AT_1METER = -59  # Calibrated value for BLE tags
    PATH_LOSS_EXPONENT = 2.0  # Indoor environment
    
    @classmethod
    def calculate_distance_from_rssi(cls, rssi):
        """Calculate distance from RSSI value"""
        if rssi == 0:
            return -1.0
        
        ratio = rssi / cls.RSSI_AT_1METER
        if ratio < 1.0:
            return math.pow(ratio, 10)
        else:
            distance = math.pow(10, (cls.RSSI_AT_1METER - rssi) / (10 * cls.PATH_LOSS_EXPONENT))
            return distance
    
    @classmethod
    def triangulate_position(cls, readings):
        """
        Triangulate position from multiple BLE readings
        readings: list of {'zone': zone, 'rssi': rssi, 'node_location': (lat, lng)}
        """
        if len(readings) < 2:
            return None
        
        # Weighted average based on signal strength
        total_weight = 0
        weighted_lat = 0
        weighted_lng = 0
        
        for reading in readings:
            # Convert RSSI to weight (stronger signal = higher weight)
            weight = math.pow(10, reading['rssi'] / 20)
            total_weight += weight
            weighted_lat += weight * reading['node_location'][0]
            weighted_lng += weight * reading['node_location'][1]
        
        if total_weight > 0:
            return {
                'latitude': weighted_lat / total_weight,
                'longitude': weighted_lng / total_weight,
                'accuracy': cls.calculate_accuracy(readings)
            }
        
        return None
    
    @classmethod
    def calculate_accuracy(cls, readings):
        """Calculate position accuracy based on signal consistency"""
        if len(readings) < 2:
            return 100.0
        
        rssi_values = [r['rssi'] for r in readings]
        variance = np.var(rssi_values)
        
        # Higher variance = lower accuracy
        accuracy = max(0, 100 - (variance / 10))
        return round(accuracy, 2)
    
    @classmethod
    def detect_zone_entry_exit(cls, visitor_id, zone_id, rssi):
        """
        Detect if visitor entered or exited a zone
        Returns 'enter', 'exit', or 'dwell'
        """
        from apps.vms.models import VisitorMovement
        
        # Get last movement for this visitor in this zone
        last_movement = VisitorMovement.objects.filter(
            visitor_id=visitor_id,
            zone_id=zone_id
        ).order_by('-timestamp').first()
        
        distance = cls.calculate_distance_from_rssi(rssi)
        
        # Define thresholds (in meters)
        ENTRY_THRESHOLD = 3.0
        EXIT_THRESHOLD = 8.0
        
        if not last_movement:
            return 'enter'
        
        if distance < ENTRY_THRESHOLD and last_movement.event_type != 'enter':
            return 'enter'
        elif distance > EXIT_THRESHOLD and last_movement.event_type == 'enter':
            return 'exit'
        else:
            return 'dwell'
    
    @classmethod
    def calculate_dwell_time(cls, visitor_id, zone_id):
        """Calculate how long visitor has been in a zone"""
        from apps.vms.models import VisitorMovement
        
        last_entry = VisitorMovement.objects.filter(
            visitor_id=visitor_id,
            zone_id=zone_id,
            event_type='enter'
        ).order_by('-timestamp').first()
        
        if not last_entry:
            return 0
        
        last_exit = VisitorMovement.objects.filter(
            visitor_id=visitor_id,
            zone_id=zone_id,
            event_type='exit',
            timestamp__gt=last_entry.timestamp
        ).order_by('-timestamp').first()
        
        if last_exit:
            return (last_exit.timestamp - last_entry.timestamp).total_seconds()
        else:
            return (timezone.now() - last_entry.timestamp).total_seconds()
    
    @classmethod
    def get_active_visitor_locations(cls):
        """
        Get current locations of all active visitors
        Returns list of visitors with coordinates
        """
        from apps.vms.models import VisitorVisit, VisitorMovement
        
        active_visits = VisitorVisit.objects.filter(
            status='active'
        ).select_related('visitor__person', 'assigned_tag')
        
        locations = []
        
        for visit in active_visits:
            # Get latest movement
            latest = VisitorMovement.objects.filter(
                visitor=visit.visitor
            ).order_by('-timestamp').first()
            
            if latest and latest.latitude and latest.longitude:
                locations.append({
                    'visitor_id': visit.visitor.id,
                    'visitor_name': visit.visitor.person.full_name,
                    'tag_uuid': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
                    'latitude': float(latest.latitude),
                    'longitude': float(latest.longitude),
                    'zone': latest.zone.name if latest.zone else None,
                    'last_seen': latest.timestamp.isoformat(),
                    'status': 'active',
                    'type': 'visitor'
                })
            elif latest and latest.zone:
                # Use zone centroid as location
                zone = latest.zone
                locations.append({
                    'visitor_id': visit.visitor.id,
                    'visitor_name': visit.visitor.person.full_name,
                    'tag_uuid': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
                    'latitude': float(zone.latitude) if zone.latitude else None,
                    'longitude': float(zone.longitude) if zone.longitude else None,
                    'zone': zone.name,
                    'last_seen': latest.timestamp.isoformat(),
                    'status': 'approximate',
                    'type': 'visitor'
                })
        
        return locations
    
    @classmethod
    def get_visitor_movement_path(cls, visitor_id, start_time=None, end_time=None):
        """
        Get movement path for a visitor over time period
        Returns GeoJSON format for map display
        """
        from apps.vms.models import VisitorMovement
        
        queryset = VisitorMovement.objects.filter(
            visitor_id=visitor_id
        ).order_by('timestamp')
        
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)
        
        # Build GeoJSON
        features = []
        coordinates = []
        
        for movement in queryset:
            if movement.latitude and movement.longitude:
                coordinates.append([movement.longitude, movement.latitude])
                
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [movement.longitude, movement.latitude]
                    },
                    'properties': {
                        'timestamp': movement.timestamp.isoformat(),
                        'event_type': movement.event_type,
                        'zone': movement.zone.name if movement.zone else None,
                        'rssi': movement.rssi,
                        'distance': round(cls.calculate_distance_from_rssi(movement.rssi), 2)
                    }
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'path': {
                'type': 'LineString',
                'coordinates': coordinates
            }
        }
        
        return geojson
    
    @classmethod
    def get_zone_heatmap_data(cls, hours=24):
        """
        Generate heatmap data for zone occupancy
        Returns data for Leaflet heatmap
        """
        from apps.vms.models import VisitorMovement
        from apps.access.models import AccessZone
        
        cutoff = timezone.now() - timedelta(hours=hours)
        
        # Aggregate movements by zone
        zone_stats = VisitorMovement.objects.filter(
            timestamp__gte=cutoff
        ).values('zone_id').annotate(
            count=Count('id'),
            avg_rssi=Avg('rssi')
        ).order_by('-count')
        
        heatmap_data = []
        
        for stat in zone_stats:
            zone = AccessZone.objects.filter(id=stat['zone_id']).first()
            if zone and zone.latitude and zone.longitude:
                # Intensity based on visitor count
                intensity = min(stat['count'] / 100, 1.0)
                heatmap_data.append({
                    'lat': float(zone.latitude),
                    'lng': float(zone.longitude),
                    'intensity': intensity,
                    'count': stat['count'],
                    'zone_name': zone.name
                })
        
        return heatmap_data
    
    @classmethod
    def detect_suspicious_movement(cls, visitor_id, hours=24):
        """
        Detect suspicious movement patterns
        Returns alerts for unusual behavior
        """
        from apps.vms.models import VisitorMovement, VisitorAlert
        from apps.access.models import AccessZone
        
        cutoff = timezone.now() - timedelta(hours=hours)
        movements = VisitorMovement.objects.filter(
            visitor_id=visitor_id,
            timestamp__gte=cutoff
        ).order_by('timestamp')
        
        alerts = []
        
        # Check for restricted zone entry
        restricted_zones = AccessZone.objects.filter(access_level__gte=3)
        restricted_entries = movements.filter(
            zone__in=restricted_zones,
            event_type='enter'
        )
        
        for entry in restricted_entries:
            alerts.append({
                'type': 'zone_breach',
                'severity': 'high',
                'zone': entry.zone.name,
                'timestamp': entry.timestamp,
                'message': f'Visitor entered restricted zone: {entry.zone.name}'
            })
        
        # Check for excessive dwell time
        for movement in movements:
            if movement.event_type == 'enter':
                dwell_time = cls.calculate_dwell_time(visitor_id, movement.zone_id)
                if dwell_time > 1800:  # 30 minutes
                    alerts.append({
                        'type': 'excessive_dwell',
                        'severity': 'medium',
                        'zone': movement.zone.name,
                        'dwell_time': dwell_time,
                        'timestamp': movement.timestamp,
                        'message': f'Visitor spent {dwell_time/60:.0f} minutes in {movement.zone.name}'
                    })
        
        # Check for rapid movement between distant zones
        prev_movement = None
        for movement in movements:
            if prev_movement and prev_movement.zone and movement.zone:
                # Calculate distance between zones
                if prev_movement.zone.distance_to(movement.zone) > 500:  # 500 meters
                    time_diff = (movement.timestamp - prev_movement.timestamp).total_seconds()
                    if time_diff < 60:  # Less than 1 minute
                        alerts.append({
                            'type': 'rapid_movement',
                            'severity': 'medium',
                            'from_zone': prev_movement.zone.name,
                            'to_zone': movement.zone.name,
                            'time_seconds': time_diff,
                            'timestamp': movement.timestamp,
                            'message': f'Unusually rapid movement from {prev_movement.zone.name} to {movement.zone.name}'
                        })
            prev_movement = movement
        
        return alerts