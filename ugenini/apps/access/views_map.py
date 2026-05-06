# apps/access/views_map.py
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.core.paginator import Paginator
import json

from apps.users.decorators import permission_required
from apps.users.permissions import VMSPermissions
from .models import AccessZone
from .map_service import AccessZoneMapService


class ZoneMapView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Main zone map view with OpenStreetMap integration
    """
    template_name = 'access/zone_map.html'
    permission_required = VMSPermissions.ACCESS_VIEW_ZONES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zones = AccessZone.objects.all()
        
        # --- Map Config ---
        context['map_config'] = self.to_json(
            AccessZoneMapService.generate_map_config(zones)
        )

        # --- Zones ---
        context['zones_geojson'] = self.to_json(
            AccessZoneMapService.get_all_zones_geojson()
        )

        # --- Stats ---
        context['stats_overlay'] = self.to_json(
            AccessZoneMapService.get_stats_overlay()
        )

        # --- Filters ---
        context['zone_types'] = AccessZone.ZoneType.choices

        # --- Selected Zone ---
        context.update(self.get_selected_zone_context())

        return context

    # -----------------------------
    # Helpers (clean CBV pattern)
    # -----------------------------

    def get_selected_zone_context(self):
        zone_id = self.request.GET.get('zone_id')

        if not zone_id:
            return {}

        try:
            zone = AccessZone.objects.only(
                'id', 'name', 'latitude', 'longitude'
            ).get(id=zone_id)

            return {
                'selected_zone': zone,
                'selected_zone_json': self.to_json({
                    'id': zone.id,
                    'name': zone.name,
                    'latitude': float(zone.latitude) if zone.latitude else None,
                    'longitude': float(zone.longitude) if zone.longitude else None
                })
            }

        except AccessZone.DoesNotExist:
            return {}

    def to_json(self, data):
        """Safe JSON serialization"""
        return json.dumps(data, cls=DjangoJSONEncoder)


class ZoneMapDataView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    API endpoint for zone map data
    """
    permission_required = VMSPermissions.ACCESS_VIEW_ZONES

    def get(self, request):
        action = request.GET.get('action', 'all')

        handlers = {
            'all': self.get_all,
            'by_type': self.get_by_type,
            'heatmap': self.get_heatmap,
            'search': self.search,
            'nearby': self.get_nearby,
            'trend': self.get_trend,
        }

        handler = handlers.get(action)

        if not handler:
            return self.error('Invalid action')

        return handler(request)

    # -------------------------
    # Handlers (clean separation)
    # -------------------------

    def get_all(self, request):
        include_occupancy = request.GET.get('occupancy', 'true') == 'true'
        data = AccessZoneMapService.get_all_zones_geojson(include_occupancy)
        return JsonResponse(data)

    def get_by_type(self, request):
        zone_type = request.GET.get('zone_type')
        if not zone_type:
            return self.error('zone_type parameter required')

        data = AccessZoneMapService.get_zones_by_type(zone_type)
        return JsonResponse(data)

    def get_heatmap(self, request):
        hours = self.get_int(request, 'hours', 24)
        data = AccessZoneMapService.get_zone_heatmap_data(hours)
        return JsonResponse({'heatmap': data})

    def search(self, request):
        query = request.GET.get('q', '')
        if not query:
            return JsonResponse({'results': []})

        data = AccessZoneMapService.search_zones(query)
        return JsonResponse({'results': data})

    def get_nearby(self, request):
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')

        if not lat or not lng:
            return self.error('lat and lng parameters required')

        try:
            lat = float(lat)
            lng = float(lng)
            radius = self.get_int(request, 'radius', 100)

            data = AccessZoneMapService.get_nearby_zones(lat, lng, radius)
            return JsonResponse({'nearby': data})

        except ValueError:
            return self.error('Invalid coordinates')

    def get_trend(self, request):
        zone_id = request.GET.get('zone_id')
        if not zone_id:
            return self.error('zone_id parameter required')

        try:
            zone_id = int(zone_id)
            hours = self.get_int(request, 'hours', 24)

            data = AccessZoneMapService.get_zone_occupancy_trend(zone_id, hours)
            return JsonResponse(data)

        except ValueError:
            return self.error('Invalid zone_id')

        except AccessZone.DoesNotExist:
            return self.error('Zone not found', status=404)

    # -------------------------
    # Utilities
    # -------------------------

    def get_int(self, request, key, default):
        try:
            return int(request.GET.get(key, default))
        except (TypeError, ValueError):
            return default

    def error(self, message, status=400):
        return JsonResponse({'error': message}, status=status)



class ZoneDetailMapView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Map view for a specific zone
    """
    template_name = 'access/zone_detail_map.html'
    permission_required = VMSPermissions.ACCESS_VIEW_ZONES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        zone = self.get_zone()

        context.update({
            'zone': zone,
            'zone_geojson': self.to_json(
                AccessZoneMapService.zone_to_geojson(zone)  # ✅ public method
            ),
            'map_config': self.to_json(
                AccessZoneMapService.get_map_config(
                    center=self.get_zone_center(zone),
                    zoom=18
                )
            ),
            'occupancy_trend': self.to_json(
                AccessZoneMapService.get_zone_occupancy_trend(zone.id)
            )
        })

        return context

    # -------------------------
    # Helpers (clean CBV pattern)
    # -------------------------

    def get_zone(self):
        return get_object_or_404(
            AccessZone.objects.only('id', 'name', 'latitude', 'longitude'),
            id=self.kwargs.get('pk')
        )

    def get_zone_center(self, zone):
        if zone.latitude and zone.longitude:
            return [float(zone.latitude), float(zone.longitude)]
        return None

    def to_json(self, data):
        return json.dumps(data, cls=DjangoJSONEncoder)



class ZoneHeatmapView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Heatmap view for zone occupancy
    """
    template_name = 'access/zone_heatmap.html'
    permission_required = VMSPermissions.ACCESS_VIEW_ZONES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hours = self.get_int('hours', 24)

        context.update({
            'map_config': self.to_json(
                AccessZoneMapService.get_map_config(show_heatmap=True)
            ),
            'hours': hours,
        })

        return context

    # -------------------------
    # Helpers
    # -------------------------

    def get_int(self, key, default):
        try:
            return int(self.request.GET.get(key, default))
        except (TypeError, ValueError):
            return default

    def to_json(self, data):
        return json.dumps(data, cls=DjangoJSONEncoder)