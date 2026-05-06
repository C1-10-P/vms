from django.urls import path
from . import views
from . import views_map

app_name = 'access'

urlpatterns = [
    #  Zone Management 
    path('zones/', views.ZoneListView.as_view(), name='zone_list'),
    path('zones/create/', views.ZoneCreateView.as_view(), name='zone_create'),
    # path('zones/<int:pk>/', views.ZoneDetailView.as_view(), name='zone_detail'),
    # path('zones/<int:pk>/edit/', views.ZoneUpdateView.as_view(), name='zone_edit'),
    path('zones/<int:pk>/delete/', views.ZoneDeleteView.as_view(), name='zone_delete'),
    path('zones/<int:pk>/toggle-status/', views.toggle_zone_status, name='zone_toggle_status'),
    path('zones/<int:pk>/edit-form/', views.get_zone_edit_form, name='zone_edit_form'),
    path('zones/<int:pk>/update/', views.update_zone, name='zone_update'),
    path('zones/<int:pk>/detail/', views.get_zone_detail, name='zone_detail'),
    # path('zones/map/', views.zone_map, name='zone_map'),

    path('zones/map/', views_map.ZoneMapView.as_view(), name='zone_map'),
    path('map/zone/<int:pk>/', views_map.ZoneDetailMapView.as_view(), name='zone_detail_map'),
    path('map/heatmap/', views_map.ZoneHeatmapView.as_view(), name='zone_heatmap'),

    # Map API Endpoints
    path('api/map-data/', views_map.ZoneMapDataView.as_view(), name='api_map_data'),
    path('zones/<int:pk>/detail/', views.ZoneDetailView.as_view(), name='zone_detail_json'),
    
    #  Permission Management 
    path('permissions/', views.PermissionListView.as_view(), name='permission_list'),
    # path('permissions/create/', views.PermissionCreateView.as_view(), name='permission_create'),
    path('permissions/create/', views.create_permission, name='permission_create'),
    path('permissions/<int:pk>/', views.PermissionDetailView.as_view(), name='permission_detail'),
    path('permissions/<int:pk>/edit/', views.PermissionUpdateView.as_view(), name='permission_edit'),
    path('permissions/<int:pk>/toggle-status/', views.toggle_permission_status, name='permission_toggle_status'),
    path('permissions/<int:pk>/delete/', views.PermissionDeleteView.as_view(), name='permission_delete'),

    path('permissions/<int:pk>/detail/', views.get_permission_detail, name='permission_detail'),
    path('permissions/<int:pk>/edit-form/', views.get_permission_edit_form, name='permission_edit_form'),
    path('permissions/<int:pk>/update/', views.update_permission, name='permission_update'),
   
    
    #  Access Logs 
    path('logs/', views.AccessLogListView.as_view(), name='log_list'),
    path('logs/<int:pk>/', views.AccessLogDetailView.as_view(), name='log_detail'),
    path('logs/export/', views.export_access_logs, name='export_logs'),
    path('logs/clear/', views.clear_access_logs, name='clear_logs'),
    
    #  2FA Management 
    path('2fa/sessions/', views.TwoFactorSessionListView.as_view(), name='tfa_list'),
    path('2fa/verify/', views.two_factor_verify, name='tfa_verify'),
    path('2fa/resend/', views.two_factor_resend, name='tfa_resend'),
    
    #  Geofencing 
    path('geofence/', views.GeofenceListView.as_view(), name='geofence_list'),
    path('geofence/create/', views.GeofenceCreateView.as_view(), name='geofence_create'),
    path('geofence/<int:pk>/', views.GeofenceDetailView.as_view(), name='geofence_detail'),
    path('geofence/<int:pk>/edit/', views.GeofenceUpdateView.as_view(), name='geofence_edit'),

    path('geofences/create/', views.create_geofence, name='geofence_create'),
    path('geofences/<int:pk>/detail/', views.get_geofence_detail, name='geofence_detail'),
    path('geofences/<int:pk>/edit-form/', views.get_geofence_edit_form, name='geofence_edit_form'),
    path('geofences/<int:pk>/update/', views.update_geofence, name='geofence_update'),

    path('geofences/<int:pk>/toggle-status/', views.toggle_geofence_status, name='geofence_toggle_status'),
    path('geofences/<int:pk>/export-geojson/', views.export_geofence_geojson, name='geofence_export_geojson'),
    path('geofences/export-all-geojson/', views.export_all_geojson, name='geofence_export_all'),

    
    #  Reports 
    path('reports/', views.AccessReportView.as_view(), name='report'),
    path('reports/summary/', views.access_summary, name='summary'),
    path('reports/failures/', views.access_failures, name='failures'),
    
    #  API Endpoints 
    path('api/request/', views.api_access_request, name='api_access_request'),
    path('api/verify/', views.api_verify_access, name='api_verify_access'),
    path('api/override/<int:pk>/', views.api_override_access, name='api_override'),
    
    #  AJAX Endpoints 
    path('ajax/check-access/', views.ajax_check_access, name='ajax_check_access'),
    path('ajax/zone-occupancy/', views.ajax_zone_occupancy, name='ajax_zone_occupancy'),
    path('ajax/current-logs/', views.ajax_current_logs, name='ajax_current_logs'),
]