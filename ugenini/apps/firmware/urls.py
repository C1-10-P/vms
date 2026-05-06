from django.urls import path
from . import views

app_name = 'firmware'

urlpatterns = [
    #  Node Management 
    path('', views.EdgeNodeListView.as_view(), name='node_list'),
    path('nodes/create/', views.EdgeNodeCreateView.as_view(), name='node_create'),
    path('nodes/<int:pk>/', views.EdgeNodeDetailView.as_view(), name='node_detail'),
    path('nodes/<int:pk>/edit/', views.EdgeNodeUpdateView.as_view(), name='node_edit'),
    path('nodes/<int:pk>/delete/', views.EdgeNodeDeleteView.as_view(), name='node_delete'),
    path('nodes/<int:pk>/reboot/', views.node_reboot, name='node_reboot'),
    path('nodes/<int:pk>/configure/', views.node_configure, name='node_configure'),
    
    #  Device Monitoring 
    path('monitor/', views.DeviceMonitorView.as_view(), name='monitor'),
    path('monitor/stats/', views.get_monitor_stats, name='monitor_stats'),
    path('monitor/health/', views.device_health_dashboard, name='health_dashboard'),
    path('monitor/heartbeats/', views.heartbeat_list, name='heartbeat_list'),
    path('nodes/<int:pk>/detail-json/', views.get_node_detail_json, name='node_detail_json'),
    path('monitor/alerts/', views.device_alerts, name='alerts'),
    
    #  Firmware Management 
    path('firmware/', views.FirmwareListView.as_view(), name='firmware_list'),
    path('firmware/upload/', views.FirmwareUploadView.as_view(), name='firmware_upload'),
    path('firmware/<int:pk>/', views.FirmwareDetailView.as_view(), name='firmware_detail'),
    path('firmware/<int:pk>/deploy/', views.firmware_deploy, name='firmware_deploy'),
    path('firmware/<int:pk>/rollback/', views.firmware_rollback, name='firmware_rollback'),
    path('firmware/<int:pk>/promote/', views.firmware_promote, name='firmware_promote'),
    path('firmware/<int:pk>/deprecate/', views.firmware_deprecate, name='firmware_deprecate'),
    
    #  OTA Updates 
    path('ota/', views.OTASessionListView.as_view(), name='ota_list'),
    path('ota/create/', views.OTASessionCreateView.as_view(), name='ota_create'),
    path('ota/<int:pk>/', views.OTASessionDetailView.as_view(), name='ota_detail'),
    path('ota/<int:pk>/cancel/', views.ota_cancel, name='ota_cancel'),
    
    #  Reports 
    path('reports/', views.DeviceReportView.as_view(), name='report'),
    path('reports/performance/', views.device_performance_report, name='performance_report'),
    path('reports/uptime/', views.uptime_report, name='uptime_report'),
    
    #  Exports 
    path('export/csv/', views.export_devices_csv, name='export_csv'),
    path('export/health/', views.export_health_report, name='export_health'),
    
    #  API Endpoints 
    path('api/heartbeat/', views.api_heartbeat, name='api_heartbeat'),
    path('api/register/', views.api_register_device, name='api_register'),
    path('api/status/<str:node_uuid>/', views.api_device_status, name='api_status'),
    path('api/config/<str:node_uuid>/', views.api_device_config, name='api_config'),
    path('api/command/<str:node_uuid>/', views.api_send_command, name='api_command'),
    
    #  AJAX Endpoints 
    path('ajax/node-status/', views.ajax_node_status, name='ajax_node_status'),
    path('ajax/update-heartbeat/', views.ajax_update_heartbeat, name='ajax_update_heartbeat'),
    path('ajax/node-metrics/<int:pk>/', views.ajax_node_metrics, name='ajax_node_metrics'),
]