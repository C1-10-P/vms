from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .movement_service import VisitorMovementService
from .map_service import OpenStreetMapService
from apps.access.models import AccessZone
from apps.core.models import Institution

class VisitorMapView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Main visitor tracking map view
    """
    template_name = 'vms/map_view.html'
    
    # Use the Mixin attribute instead of the decorator
    permission_required = VMSPermissions.VISITOR_TRACK
    
    # The dispatch method no longer needs the @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
    
        # Check for geofence_coordinates instead of latitude/longitude
        zones = AccessZone.objects.filter(
            is_active=True
        ).exclude(
            geofence_coordinates__isnull=True
        )
        
        # Get active visitor locations
        visitors = VisitorMovementService.get_active_visitor_locations()
        
        # Generate map configuration
        map_config = OpenStreetMapService.generate_map_config(zones, visitors)
        
        context['map_config'] = json.dumps(map_config)
        context['zones'] = zones
        context['active_visitors'] = len(visitors)
        context['total_zones'] = zones.count()
        
        # Get heatmap data
        context['heatmap_data'] = json.dumps(
            VisitorMovementService.get_zone_heatmap_data(hours=24)
        )
        
        return context


class VisitorMovementDataView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    API endpoint for visitor movement data
    Returns GeoJSON for map display
    """
    
    # 1. Standard CBV permission check
    permission_required = VMSPermissions.VISITOR_TRACK
    
    # 2. Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        visitor_id = request.GET.get('visitor_id')
        # Use a try-except or default if hours isn't a valid integer
        try:
            hours = int(request.GET.get('hours', 24))
        except ValueError:
            hours = 24
        
        if visitor_id:
            end_time = timezone.now()
            start_time = end_time - timedelta(hours=hours)
            
            geojson = VisitorMovementService.get_visitor_movement_path(
                visitor_id, start_time, end_time
            )
            
            return JsonResponse(geojson)
        
        # Return all active visitor locations
        locations = VisitorMovementService.get_active_visitor_locations()
        return JsonResponse({'visitors': locations}, safe=False)


class VisitorHeatmapView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Heatmap data endpoint for zone occupancy
    """
    
    # 1. Standard CBV permission check
    permission_required = VMSPermissions.VISITOR_TRACK
    
    # 2. Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        hours = int(request.GET.get('hours', 24))
        data = VisitorMovementService.get_zone_heatmap_data(hours)
        return JsonResponse({'heatmap': data})


class VisitorTimelineView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Timeline view for visitor movement replay
    """
    template_name = 'vms/timeline_view.html'
    
    # 1. Standard CBV permission check
    permission_required = VMSPermissions.VISITOR_TRACK
    
    # 2. Removed the broken @permission_required decorator
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['visitor_id'] = self.kwargs.get('visitor_id')
        return context


class VisitorMovementAPIView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    REST API for visitor movement data
    """
    
    permission_required = VMSPermissions.VISITOR_TRACK
    
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        action = request.GET.get('action')
        
        if action == 'active':
            # Get active visitors from the database
            from apps.vms.models import VisitorVisit
            
            active_visits = VisitorVisit.objects.filter(
                status='active'
            ).select_related('visitor__person', 'assigned_tag')
            
            locations = []
            for visit in active_visits:
                locations.append({
                    'visitor_id': visit.visitor.id,
                    # This is failing because .get_full_name() doesn't exist
                    # Directly access the fields
                    'visitor_name': f"{visit.visitor.person.first_name} {visit.visitor.person.last_name}".strip() or "Unknown Visitor",
                    'tag_uuid': visit.assigned_tag.tag_uuid if visit.assigned_tag else None,
                    'latitude': None,
                    'longitude': None,
                    'zone': None,
                    'last_seen': visit.check_in_time.isoformat() if visit.check_in_time else None,
                    'status': 'active',
                    'type': 'visitor'
                })
            
            return JsonResponse({'success': True, 'data': locations})
        
        elif action == 'path':
            visitor_id = request.GET.get('visitor_id')
            hours = int(request.GET.get('hours', 24))
            end_time = timezone.now()
            start_time = end_time - timedelta(hours=hours)
            
            from apps.vms.models import VisitorMovement
            
            movements = VisitorMovement.objects.filter(
                visitor_id=visitor_id,
                timestamp__gte=start_time,
                timestamp__lte=end_time
            ).order_by('timestamp').select_related('zone')
            
            features = []
            coordinates = []
            
            for movement in movements:
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
                            'rssi': movement.rssi
                        }
                    })
            
            # Get visitor info
            from apps.vms.models import Visitor
            try:
                visitor = Visitor.objects.select_related('person', 'assigned_tag').get(id=visitor_id)
                visitor_name = visitor.person.get_full_name() or f"{visitor.person.first_name} {visitor.person.last_name}"
                tag_uuid = visitor.assigned_tag.tag_uuid if visitor.assigned_tag else None
            except Visitor.DoesNotExist:
                visitor_name = "Unknown"
                tag_uuid = None
            
            geojson = {
                'type': 'FeatureCollection',
                'features': features,
                'path': {
                    'type': 'LineString',
                    'coordinates': coordinates
                },
                'visitor_name': visitor_name,
                'tag_uuid': tag_uuid
            }
            
            return JsonResponse(geojson)
        
        elif action == 'heatmap':
            hours = int(request.GET.get('hours', 24))
            cutoff = timezone.now() - timedelta(hours=hours)
            
            from apps.vms.models import VisitorMovement
            from django.db.models import Count
            
            zone_stats = VisitorMovement.objects.filter(
                timestamp__gte=cutoff
            ).values('zone_id').annotate(
                count=Count('id')
            ).order_by('-count')
            
            heatmap_data = []
            for stat in zone_stats:
                from apps.access.models import AccessZone
                try:
                    zone = AccessZone.objects.get(id=stat['zone_id'])
                    if zone.latitude and zone.longitude:
                        intensity = min(stat['count'] / 50, 1.0)
                        heatmap_data.append({
                            'lat': float(zone.latitude),
                            'lng': float(zone.longitude),
                            'intensity': intensity,
                            'count': stat['count'],
                            'zone_name': zone.name
                        })
                except AccessZone.DoesNotExist:
                    pass
            
            return JsonResponse({'success': True, 'data': heatmap_data})
        
        elif action == 'suspicious':
            visitor_id = request.GET.get('visitor_id')
            alerts = VisitorMovementService.detect_suspicious_movement(visitor_id)
            return JsonResponse({'success': True, 'alerts': alerts})
        
        return JsonResponse({'error': 'Invalid action'}, status=400)