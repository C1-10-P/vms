import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class VMSConsumer(AsyncWebsocketConsumer):
    """
    Main WebSocket consumer for VMS real-time updates
    Handles multiple channel groups for different event types
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope.get('user', AnonymousUser())
        
        if self.user.is_authenticated:
            # User-specific room
            self.user_room = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.user_room, self.channel_name)
            
            # Role-based rooms
            if self.user.is_superuser or self.user.is_staff:
                await self.channel_layer.group_add("admin", self.channel_name)
            
            if hasattr(self.user, 'person'):
                if self.user.person.person_type == 'staff':
                    staff = await self.get_staff_profile()
                    if staff and staff.staff_category == 'academic':
                        await self.channel_layer.group_add("lecturers", self.channel_name)
                    elif staff and staff.staff_category == 'security':
                        await self.channel_layer.group_add("security", self.channel_name)
            
            # Default rooms
            await self.channel_layer.group_add("attendance_live", self.channel_name)
            await self.channel_layer.group_add("visitor_tracking", self.channel_name)
            await self.channel_layer.group_add("device_health", self.channel_name)
            await self.channel_layer.group_add("security_alerts", self.channel_name)
            
            await self.accept()
            
            # Send initial connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection',
                'status': 'connected',
                'user_id': self.user.id,
                'timestamp': timezone.now().isoformat()
            }))
            
            logger.info(f"WebSocket connected: {self.user.username}")
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_room'):
            await self.channel_layer.group_discard(self.user_room, self.channel_name)
        
        await self.channel_layer.group_discard("attendance_live", self.channel_name)
        await self.channel_layer.group_discard("visitor_tracking", self.channel_name)
        await self.channel_layer.group_discard("device_health", self.channel_name)
        await self.channel_layer.group_discard("security_alerts", self.channel_name)
        
        logger.info(f"WebSocket disconnected: {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong', 'timestamp': timezone.now().isoformat()}))
            
            elif message_type == 'subscribe':
                await self.handle_subscribe(data)
            
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe(data)
            
            elif message_type == 'get_stats':
                await self.send_stats()
            
        except json.JSONDecodeError:
            logger.error(f"Invalid WebSocket message: {text_data}")
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
    
    async def handle_subscribe(self, data):
        """Subscribe to additional channels"""
        channels = data.get('channels', [])
        
        for channel in channels:
            group_name = f"channel_{channel}"
            await self.channel_layer.group_add(group_name, self.channel_name)
        
        await self.send(text_data=json.dumps({
            'type': 'subscribed',
            'channels': channels
        }))
    
    async def handle_unsubscribe(self, data):
        """Unsubscribe from channels"""
        channels = data.get('channels', [])
        
        for channel in channels:
            group_name = f"channel_{channel}"
            await self.channel_layer.group_discard(group_name, self.channel_name)
        
        await self.send(text_data=json.dumps({
            'type': 'unsubscribed',
            'channels': channels
        }))
    
    async def send_stats(self):
        """Send current statistics to client"""
        stats = await self.get_realtime_stats()
        await self.send(text_data=json.dumps({
            'type': 'stats',
            'data': stats
        }))
    
    # ============ Event Handlers ============
    
    async def attendance_update(self, event):
        """Send attendance update to client"""
        await self.send(text_data=json.dumps({
            'type': 'attendance',
            'data': event['data']
        }))
    
    async def visitor_update(self, event):
        """Send visitor update to client"""
        await self.send(text_data=json.dumps({
            'type': 'visitor',
            'data': event['data']
        }))
    
    async def device_update(self, event):
        """Send device status update to client"""
        await self.send(text_data=json.dumps({
            'type': 'device',
            'data': event['data']
        }))
    
    async def security_alert(self, event):
        """Send security alert to client"""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'severity': event.get('severity', 'info'),
            'data': event['data']
        }))
    
    async def notification(self, event):
        """Send user notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    async def occupancy_update(self, event):
        """Send zone occupancy update to client"""
        await self.send(text_data=json.dumps({
            'type': 'occupancy',
            'data': event['data']
        }))
    
    # ============ Database Helpers ============
    
    @database_sync_to_async
    def get_staff_profile(self):
        """Get staff profile for user"""
        from apps.core.models import Staff
        try:
            return Staff.objects.get(person__system_user=self.user)
        except Staff.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_realtime_stats(self):
        """Get real-time statistics"""
        from apps.classroom.models import ClassAttendance
        from apps.vms.models import VisitorVisit
        from apps.firmware.models import EdgeNode
        
        return {
            'current_attendance': ClassAttendance.objects.filter(
                scan_time__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).count(),
            'active_visitors': VisitorVisit.objects.filter(status='active').count(),
            'online_devices': EdgeNode.objects.filter(status='online').count(),
            'timestamp': timezone.now().isoformat()
        }


class AttendanceConsumer(AsyncWebsocketConsumer):
    """
    Dedicated WebSocket consumer for attendance real-time feed
    """
    
    async def connect(self):
        self.room_name = 'attendance_feed'
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data.get('type') == 'get_recent':
            recent = await self.get_recent_attendance()
            await self.send(text_data=json.dumps({
                'type': 'recent',
                'data': recent
            }))
    
    async def attendance_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'event',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_recent_attendance(self):
        from apps.classroom.models import ClassAttendance
        attendances = ClassAttendance.objects.select_related(
            'student__person', 'class_obj'
        ).order_by('-scan_time')[:20]
        
        return [{
            'id': a.id,
            'student_name': a.student.person.full_name,
            'student_reg': a.student.student_reg_number,
            'class_code': a.class_obj.class_code,
            'time': a.scan_time.isoformat(),
            'status': a.verification_status
        } for a in attendances]


class VisitorTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for visitor real-time tracking
    """
    
    async def connect(self):
        self.visitor_id = self.scope['url_route']['kwargs'].get('visitor_id')
        self.room_name = f'visitor_{self.visitor_id}' if self.visitor_id else 'visitor_tracking'
        
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
    
    async def visitor_movement(self, event):
        await self.send(text_data=json.dumps({
            'type': 'movement',
            'data': event['data']
        }))
    
    async def visitor_alert(self, event):
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': event['data']
        }))


class DeviceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for device monitoring
    """
    
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs'].get('device_id')
        self.room_name = f'device_{self.device_id}' if self.device_id else 'device_monitoring'
        
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
    
    async def device_heartbeat(self, event):
        await self.send(text_data=json.dumps({
            'type': 'heartbeat',
            'data': event['data']
        }))
    
    async def device_alert(self, event):
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': event['data']
        }))


class ZoneConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for zone occupancy tracking
    """
    
    async def connect(self):
        self.zone_id = self.scope['url_route']['kwargs'].get('zone_id')
        self.room_name = f'zone_{self.zone_id}' if self.zone_id else 'zone_occupancy'
        
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        
        # Send initial occupancy
        await self.send_occupancy()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
    
    async def occupancy_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'occupancy',
            'data': event['data']
        }))
    
    async def send_occupancy(self):
        occupancy = await self.get_zone_occupancy()
        await self.send(text_data=json.dumps({
            'type': 'initial_occupancy',
            'data': occupancy
        }))
    
    @database_sync_to_async
    def get_zone_occupancy(self):
        from apps.access.models import AccessZone
        if self.zone_id:
            zone = AccessZone.objects.get(id=self.zone_id)
            return {
                'zone_id': zone.id,
                'zone_name': zone.name,
                'current': zone.current_occupancy,
                'capacity': zone.capacity,
                'percentage': (zone.current_occupancy / zone.capacity * 100) if zone.capacity > 0 else 0
            }
        return None