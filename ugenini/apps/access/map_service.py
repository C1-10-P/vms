# apps/access/map_service.py
import json
import math
import requests
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count, Avg, Q
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AccessZoneMapService:
    """
    Service for OpenStreetMap integration for access zones
    Handles geofencing, zone boundaries, and real-time occupancy visualization
    """
    OSM_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OSM_ROUTING_URL = "https://router.project-osrm.org/route/v1/driving/"

    # Map configuration
    DEFAULT_CENTER = [-1.2921, 36.8219]  # JKUAT Main Campus
    DEFAULT_ZOOM = 16
    
    # Color schemes for different zone types
    ZONE_COLORS = {
        'campus': '#10b981',      # Green
        'building': '#3b82f6',    # Blue
        'floor': '#8b5cf6',       # Purple
        'lab': '#ef4444',         # Red
        'office': '#f59e0b',      # Amber
        'classroom': '#06b6d4',   # Cyan
        'library': '#8b5cf6',     # Purple
        'restricted': '#dc2626',  # Dark Red
        'research': '#ec4899',    # Pink
        'server_room': '#6366f1', # Indigo
    }
    
    # Occupancy-based color modifiers
    OCCUPANCY_COLORS = {
        'empty': '#22c55e',       # Green - < 20%
        'moderate': '#eab308',    # Yellow - 20-60%
        'busy': '#f97316',        # Orange - 60-85%
        'full': '#ef4444',        # Red - > 85%
    }
    
    @classmethod
    def geocode_address(cls, address):
        """Convert address to coordinates using Nominatim"""
        cache_key = f"geocode_{address}"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            
            response = requests.get(cls.OSM_NOMINATIM_URL, params=params, headers={
                'User-Agent': 'VMS/1.0 (Visitor Management System)'
            })
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    result = {
                        'latitude': float(data[0]['lat']),
                        'longitude': float(data[0]['lon']),
                        'display_name': data[0]['display_name']
                    }
                    cache.set(cache_key, result, 86400)  # Cache for 24 hours
                    return result
            
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
        
        return None
    
    @classmethod
    def get_route(cls, start_lat, start_lng, end_lat, end_lng):
        """Get route between two points using OSRM"""
        cache_key = f"route_{start_lat}_{start_lng}_{end_lat}_{end_lng}"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            url = f"{cls.OSM_ROUTING_URL}{start_lng},{start_lat};{end_lng},{end_lat}"
            params = {
                'overview': 'full',
                'geometries': 'geojson'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'Ok':
                    route = data['routes'][0]
                    result = {
                        'distance_km': route['distance'] / 1000,
                        'duration_minutes': route['duration'] / 60,
                        'geometry': route['geometry'],
                        'steps': [
                            {
                                'distance': step['distance'],
                                'duration': step['duration'],
                                'instruction': step.get('name', 'Continue')
                            }
                            for step in route.get('legs', [{}])[0].get('steps', [])
                        ]
                    }
                    cache.set(cache_key, result, 3600)  # Cache for 1 hour
                    return result
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
        
        return None

    @classmethod
    def get_map_tile_url(cls):
        """Get OpenStreetMap tile URL"""
        return "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    
    @classmethod
    def get_map_attribution(cls):
        """Get map attribution text"""
        return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    

    @classmethod
    def get_zone_color(cls, zone, include_occupancy=True):
        """
        Get color for a zone based on type and occupancy
        """
        base_color = cls.ZONE_COLORS.get(zone.zone_type, '#6b7280')
        
        if include_occupancy and zone.capacity > 0:
            occupancy_percentage = (zone.current_occupancy / zone.capacity) * 100
            
            if occupancy_percentage >= 85:
                return cls.OCCUPANCY_COLORS['full']
            elif occupancy_percentage >= 60:
                return cls.OCCUPANCY_COLORS['busy']
            elif occupancy_percentage >= 20:
                return cls.OCCUPANCY_COLORS['moderate']
            else:
                return cls.OCCUPANCY_COLORS['empty']
        
        return base_color
    
    @classmethod
    def get_all_zones_geojson(cls, include_occupancy=True) -> Dict:
        """
        Get all access zones as GeoJSON for map display
        """
        from apps.access.models import AccessZone
        
        zones = AccessZone.objects.filter(is_active=True).select_related(
            'institution', 'college', 'school', 'department', 'parent_zone'
        )
        
        features = []
        
        for zone in zones:
            feature = cls._zone_to_geojson_feature(zone, include_occupancy)
            if feature:
                features.append(feature)
        
        return {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'total_zones': len(features),
                'last_updated': timezone.now().isoformat(),
                'center': cls.DEFAULT_CENTER,
                'zoom': cls.DEFAULT_ZOOM
            }
        }
    
    @classmethod
    def _zone_to_geojson_feature(cls, zone, include_occupancy=True):
        geometry = None

        coords = zone.geofence_coordinates

        if coords:
            # Case 1: dict (GeoJSON-like)
            if isinstance(coords, dict) and coords.get('coordinates'):
                geometry = {
                    'type': 'Polygon',
                    'coordinates': coords['coordinates']
                }

            # Case 2: list (raw coordinates)
            elif isinstance(coords, list):
                geometry = {
                    'type': 'Polygon',
                    'coordinates': [coords]  # wrap for GeoJSON standard
                }

            # Case 3: fallback (single point)
            else:
                geometry = {
                    'type': 'Point',
                    'coordinates': coords
                }
            return geometry
        
        # Calculate occupancy percentage
        occupancy_percentage = 0
        if zone.capacity > 0:
            occupancy_percentage = (zone.current_occupancy / zone.capacity) * 100
        
        properties = {
            'id': zone.id,
            'name': zone.name,
            'code': zone.code,
            'zone_type': zone.zone_type,
            'zone_type_display': zone.get_zone_type_display(),
            'access_level': zone.access_level,
            'access_level_display': zone.get_access_level_display(),
            'description': zone.description,
            'building': zone.building,
            'floor': zone.floor,
            'room_number': zone.room_number,
            'capacity': zone.capacity,
            'current_occupancy': zone.current_occupancy,
            'occupancy_percentage': round(occupancy_percentage, 1),
            'requires_2fa': zone.requires_2fa,
            'requires_escort': zone.requires_escort,
            'is_open': zone.is_open(),
            'color': cls.get_zone_color(zone, include_occupancy),
            'stroke_color': cls.get_zone_color(zone, False),
            'fill_opacity': 0.4 if include_occupancy else 0.2,
            'stroke_width': 2,
            'stroke_opacity': 0.8,
        }
        
        # Add hierarchy info
        if zone.parent_zone:
            properties['parent_zone'] = zone.parent_zone.name
            properties['parent_zone_id'] = zone.parent_zone.id
        
        if zone.institution:
            properties['institution'] = zone.institution.name
        
        return {
            'type': 'Feature',
            'geometry': geometry,
            'properties': properties
        }
    
    @classmethod
    def get_zones_by_type(cls, zone_type: str, include_occupancy=True) -> Dict:
        """
        Get zones filtered by type as GeoJSON
        """
        from apps.access.models import AccessZone
        
        zones = AccessZone.objects.filter(
            zone_type=zone_type,
            is_active=True
        )
        
        features = []
        for zone in zones:
            feature = cls._zone_to_geojson_feature(zone, include_occupancy)
            if feature:
                features.append(feature)
        
        return {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'zone_type': zone_type,
                'count': len(features),
                'last_updated': timezone.now().isoformat()
            }
        }
    
    @classmethod
    def get_zone_heatmap_data(cls, hours=24) -> List[Dict]:
        """
        Generate heatmap data for zone occupancy
        Returns data for Leaflet heatmap
        """
        from apps.access.models import AccessZone
        from apps.vms.models import VisitorMovement
        
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        
        # Get zones with coordinates
        zones = AccessZone.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        heatmap_data = []
        
        for zone in zones:
            # Calculate intensity based on recent movements
            recent_movements = VisitorMovement.objects.filter(
                zone=zone,
                timestamp__gte=cutoff,
                event_type='enter'
            ).count()
            
            # Normalize intensity (max 100)
            intensity = min(recent_movements / 50, 1.0)
            
            if intensity > 0:
                heatmap_data.append({
                    'lat': float(zone.latitude),
                    'lng': float(zone.longitude),
                    'intensity': intensity,
                    'count': recent_movements,
                    'zone_name': zone.name,
                    'zone_id': zone.id
                })
        
        return heatmap_data
    
    @classmethod
    def get_zone_occupancy_trend(cls, zone_id: int, hours=24) -> Dict:
        """
        Get occupancy trend data for a specific zone
        """
        from apps.access.models import AccessZone
        from apps.vms.models import VisitorMovement
        from django.db.models import Count
        from django.db.models.functions import TruncHour
        
        zone = AccessZone.objects.get(id=zone_id)
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        
        # Get hourly occupancy data
        movements = VisitorMovement.objects.filter(
            zone=zone,
            timestamp__gte=cutoff,
            event_type='enter'
        ).annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        # Build trend data
        trend = []
        current = cutoff
        while current <= timezone.now():
            hour_key = current.replace(minute=0, second=0, microsecond=0)
            movement = next((m for m in movements if m['hour'] == hour_key), None)
            trend.append({
                'hour': hour_key.strftime('%Y-%m-%d %H:00'),
                'occupancy': movement['count'] if movement else 0
            })
            current += timezone.timedelta(hours=1)
        
        return {
            'zone_id': zone.id,
            'zone_name': zone.name,
            'capacity': zone.capacity,
            'current_occupancy': zone.current_occupancy,
            'occupancy_percentage': (zone.current_occupancy / zone.capacity * 100) if zone.capacity > 0 else 0,
            'trend': trend,
            'peak_hour': max(trend, key=lambda x: x['occupancy']) if trend else None
        }
    
    @classmethod
    def search_zones(cls, query: str, limit=20) -> List[Dict]:
        """
        Search zones by name, code, or building
        """
        from apps.access.models import AccessZone
        
        zones = AccessZone.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(building__icontains=query) |
            Q(room_number__icontains=query),
            is_active=True
        )[:limit]
        
        results = []
        for zone in zones:
            results.append({
                'id': zone.id,
                'name': zone.name,
                'code': zone.code,
                'zone_type': zone.get_zone_type_display(),
                'building': zone.building,
                'floor': zone.floor,
                'room_number': zone.room_number,
                'current_occupancy': zone.current_occupancy,
                'capacity': zone.capacity,
                'latitude': float(zone.latitude) if zone.latitude else None,
                'longitude': float(zone.longitude) if zone.longitude else None,
                'color': cls.get_zone_color(zone)
            })
        
        return results
    
    @classmethod
    def get_nearby_zones(cls, latitude: float, longitude: float, radius_meters: int = 100) -> List[Dict]:
        """
        Find zones near a given location
        """
        from apps.access.models import AccessZone
        
        # This is a simplified version - in production, use PostGIS for proper spatial queries
        zones = AccessZone.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        nearby = []
        for zone in zones:
            distance = cls._haversine_distance(
                latitude, longitude,
                float(zone.latitude), float(zone.longitude)
            )
            
            if distance <= radius_meters:
                nearby.append({
                    'id': zone.id,
                    'name': zone.name,
                    'distance_meters': round(distance, 1),
                    'zone_type': zone.get_zone_type_display(),
                    'current_occupancy': zone.current_occupancy,
                    'capacity': zone.capacity,
                    'latitude': float(zone.latitude),
                    'longitude': float(zone.longitude)
                })
        
        return sorted(nearby, key=lambda x: x['distance_meters'])
    
    @classmethod
    def _haversine_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in meters using Haversine formula
        """
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    # @classmethod
    # def get_map_config(cls, center=None, zoom=None, show_heatmap=False) -> Dict:
    #     """
    #     Get map configuration for frontend
    #     """
    #     return {
    #         'center': center or cls.DEFAULT_CENTER,
    #         'zoom': zoom or cls.DEFAULT_ZOOM,
    #         'tile_url': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    #         'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    #         'max_zoom': 19,
    #         'min_zoom': 12,
    #         'show_heatmap': show_heatmap,
    #         'heatmap_config': {
    #             'radius': 25,
    #             'blur': 15,
    #             'max_zoom': 17,
    #             'min_opacity': 0.3
    #         } if show_heatmap else None
    #     }
    @classmethod
    def generate_map_config(cls, zones, center_lat=None, center_lng=None, zoom=15):
        """
        Generate map configuration JSON for frontend
        """
        valid_zones = []
    
        # 1. Pre-process zones to get usable coordinates
        for z in zones:
            coords = None
            if z.geofence_coordinates and isinstance(z.geofence_coordinates, list) and len(z.geofence_coordinates) > 0:
                # Handle both Polygon [[[lng, lat]]] and Point [lng, lat]
                first_coord = z.geofence_coordinates[0]
                coords = first_coord if isinstance(first_coord, (int, float)) else first_coord[0]
            
            if coords:
                z.temp_lng = coords[0] if isinstance(coords, list) else z.geofence_coordinates[0]
                z.temp_lat = coords[1] if isinstance(coords, list) else z.geofence_coordinates[1]
                valid_zones.append(z)

            # 2. Calculate center BEFORE initializing map_config if missing
            if not center_lat or not center_lng:
                if valid_zones:
                    center_lat = sum(z.temp_lat for z in valid_zones) / len(valid_zones)
                    center_lng = sum(z.temp_lng for z in valid_zones) / len(valid_zones)
                else:
                    # Default fallback (e.g., center of your campus or 0,0)
                    center_lat, center_lng = -1.1018, 37.0144  # Example: Juja/JKUAT coordinates

            # 3. INITIALIZE map_config HERE (guarantees it exists for the return statement)
            map_config = {
                'center': [center_lat, center_lng],
                'zoom': zoom,
                'tile_url': cls.get_map_tile_url(),
                'attribution': cls.get_map_attribution(),
                'zones': [],
                'visitors': [],
                'heatmap': [],
                'paths': []
            }
    
            # 4. Populate zones
            for zone in zones:
                if zone.geofence_coordinates:
                    # Check if it's a Polygon or Point
                    is_polygon = isinstance(zone.geofence_coordinates[0], list)
                    
                    map_config['zones'].append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon' if is_polygon else 'Point',
                            'coordinates': [zone.geofence_coordinates] if is_polygon else zone.geofence_coordinates
                        },
                        'properties': {
                            'name': zone.name,
                            'zone_type': zone.zone_type,
                            'access_level': zone.access_level,
                            'current_occupancy': zone.current_occupancy,
                            'capacity': zone.capacity,
                            # 'color': cls._get_zone_color(zone)
                        }
                    })
            return map_config

    @classmethod
    def get_stats_overlay(cls) -> Dict:
        """
        Get statistics overlay data for map
        """
        from apps.access.models import AccessZone
        
        zones = AccessZone.objects.filter(is_active=True)
        
        total_capacity = zones.aggregate(total=models.Sum('capacity'))['total'] or 0
        total_occupancy = zones.aggregate(total=models.Sum('current_occupancy'))['total'] or 0
        
        return {
            'total_zones': zones.count(),
            'zones_by_type': list(zones.values('zone_type').annotate(count=Count('id'))),
            'total_capacity': total_capacity,
            'total_occupancy': total_occupancy,
            'overall_occupancy_percentage': round((total_occupancy / total_capacity * 100), 1) if total_capacity > 0 else 0,
            'restricted_zones': zones.filter(access_level__gte=3).count(),
            'zones_requiring_2fa': zones.filter(requires_2fa=True).count(),
            'zones_at_capacity': zones.filter(current_occupancy__gte=models.F('capacity')).count() if total_capacity > 0 else 0
        }


# For Django models import
from django.db import models

@staticmethod
def zone_to_geojson(zone):
    return AccessZoneMapService._zone_to_geojson_feature(zone)

# def get_heatmap_map_config():
#     return get_map_config(show_heatmap=True)