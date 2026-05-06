from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Main VMS WebSocket
    re_path(r'ws/vms/$', consumers.VMSConsumer.as_asgi(), name='vms_ws'),
    
    # Attendance WebSocket
    re_path(r'ws/attendance/$', consumers.AttendanceConsumer.as_asgi(), name='attendance_ws'),
    
    # Visitor tracking WebSocket
    re_path(r'ws/visitors/$', consumers.VisitorTrackingConsumer.as_asgi(), name='visitor_ws'),
    re_path(r'ws/visitors/(?P<visitor_id>\w+)/$', consumers.VisitorTrackingConsumer.as_asgi(), name='visitor_detail_ws'),
    
    # Device monitoring WebSocket
    re_path(r'ws/devices/$', consumers.DeviceConsumer.as_asgi(), name='device_ws'),
    re_path(r'ws/devices/(?P<device_id>\w+)/$', consumers.DeviceConsumer.as_asgi(), name='device_detail_ws'),
    
    # Zone occupancy WebSocket
    re_path(r'ws/zones/$', consumers.ZoneConsumer.as_asgi(), name='zone_ws'),
    re_path(r'ws/zones/(?P<zone_id>\w+)/$', consumers.ZoneConsumer.as_asgi(), name='zone_detail_ws'),
    
    # Alerts WebSocket
    re_path(r'ws/alerts/$', consumers.ZoneConsumer.as_asgi(), name='alert_ws'),
]