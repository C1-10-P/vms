import json
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class OpenStreetMapService:
    """
    Service for OpenStreetMap integration
    Handles geocoding, routing, and map visualization
    """
    
    OSM_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OSM_ROUTING_URL = "https://router.project-osrm.org/route/v1/driving/"
    
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
    def generate_map_config(cls, zones, visitors, center_lat=None, center_lng=None, zoom=15):
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
                            'color': cls._get_zone_color(zone)
                        }
                    })
    
            # 5. Populate visitors
            for visitor in visitors:
                if visitor.get('latitude') and visitor.get('longitude'):
                    map_config['visitors'].append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [float(visitor['longitude']), float(visitor['latitude'])]
                        },
                        'properties': {
                            'visitor_id': visitor['visitor_id'],
                            'name': visitor['visitor_name'],
                            'tag_uuid': visitor.get('tag_uuid'),
                            'last_seen': visitor.get('last_seen'),
                            'status': visitor.get('status'),
                            'icon': 'visitor-marker'
                        }
                    })
            
            return map_config # Now map_config is guaranteed to be associated with a value
    
    @classmethod
    def _get_zone_color(cls, zone):
        """Get color for zone based on type and occupancy"""
        if zone.current_occupancy >= zone.capacity and zone.capacity > 0:
            return '#dc3545'  # Red - Full
        elif zone.current_occupancy > zone.capacity * 0.8:
            return '#ffc107'  # Yellow - Near capacity
        elif zone.access_level >= 3:
            return '#6f42c1'  # Purple - Restricted
        elif zone.zone_type == 'restricted':
            return '#fd7e14'  # Orange - Restricted area
        else:
            return '#28a745'  # Green - Normal
        
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
        
            location_data = {
                'visitor_id': visit.visitor.id,
                'visitor_name': visit.visitor.person.get_full_name() or f"{visit.visitor.person.first_name} {visit.visitor.person.last_name}",
                'tag_uuid': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
                'last_seen': (latest.timestamp if latest else visit.check_in_time).isoformat(),
                'status': 'active',
                'type': 'visitor'
            }
            
            if latest and latest.latitude and latest.longitude:
                location_data.update({
                    'latitude': float(latest.latitude),
                    'longitude': float(latest.longitude),
                    'zone': latest.zone.name if latest.zone else None,
                    'accuracy': 'gps'
                })
            elif latest and latest.zone and latest.zone.latitude and latest.zone.longitude:
                location_data.update({
                    'latitude': float(latest.zone.latitude),
                    'longitude': float(latest.zone.longitude),
                    'zone': latest.zone.name,
                    'accuracy': 'approximate'
                })
            else:
                location_data.update({
                    'latitude': None,
                    'longitude': None,
                    'zone': 'Unknown',
                    'accuracy': 'unknown'
                })
            
            locations.append(location_data)
        
        return locations