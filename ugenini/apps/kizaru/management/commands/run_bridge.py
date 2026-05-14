import json
import threading
import paho.mqtt.client as mqtt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MQTTBridge:
    """
    Bridge between MQTT messages and WebSocket channels
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        from paho.mqtt.enums import CallbackAPIVersion

        self.client = mqtt.Client(CallbackAPIVersion.VERSION1)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.channel_layer = get_channel_layer()
        self._initialized = True
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            logger.info("MQTT Bridge connected to broker")
            # Subscribe to all VMS topics
            self.client.subscribe("jkuat/#")
        else:
            logger.error(f"MQTT Bridge connection failed: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Process incoming MQTT messages and forward to WebSocket"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Route to appropriate WebSocket groups
            if topic.startswith("jkuat/attendance/"):
                self._route_attendance(topic, payload)
            elif topic.startswith("jkuat/visitor/"):
                self._route_visitor(topic, payload)
            elif topic.startswith("jkuat/system/"):
                self._route_system(topic, payload)
            elif topic.startswith("jkuat/security/"):
                self._route_security(topic, payload)
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {msg.payload}")
        except Exception as e:
            logger.error(f"MQTT bridge error: {e}")
    
    def _route_attendance(self, topic, payload):
        """Route attendance messages to WebSocket"""
        if topic == "jkuat/attendance/class/sign_in":
            async_to_sync(self.channel_layer.group_send)(
                "attendance_live",
                {
                    'type': 'attendance_update',
                    'data': {
                        'student_id': payload.get('student_id'),
                        'student_name': payload.get('student_name', 'Unknown'),
                        'class_code': payload.get('class_code'),
                        'timestamp': payload.get('timestamp'),
                        'method': payload.get('method', 'qr')
                    }
                }
            )
            
            # Also send to user-specific room if applicable
            if 'user_id' in payload:
                async_to_sync(self.channel_layer.group_send)(
                    f"user_{payload['user_id']}",
                    {
                        'type': 'notification',
                        'data': {
                            'title': 'Attendance Recorded',
                            'message': f"Your attendance for {payload.get('class_code')} has been recorded.",
                            'type': 'attendance'
                        }
                    }
                )
    
    def _route_visitor(self, topic, payload):
        """Route visitor messages to WebSocket"""
        if topic == "jkuat/visitor/tag/ping":
            async_to_sync(self.channel_layer.group_send)(
                "visitor_tracking",
                {
                    'type': 'visitor_update',
                    'data': {
                        'visitor_id': payload.get('visitor_id'),
                        'visitor_name': payload.get('visitor_name'),
                        'location': payload.get('location'),
                        'rssi': payload.get('rssi'),
                        'timestamp': payload.get('timestamp')
                    }
                }
            )
            
            # Send to visitor-specific room
            if 'visitor_id' in payload:
                async_to_sync(self.channel_layer.group_send)(
                    f"visitor_{payload['visitor_id']}",
                    {
                        'type': 'visitor_movement',
                        'data': {
                            'location': payload.get('location'),
                            'timestamp': payload.get('timestamp')
                        }
                    }
                )
        
        elif topic == "jkuat/visitor/alert/zone_breach":
            async_to_sync(self.channel_layer.group_send)(
                "security_alerts",
                {
                    'type': 'security_alert',
                    'severity': 'high',
                    'data': {
                        'alert_type': 'zone_breach',
                        'visitor_name': payload.get('visitor_name'),
                        'zone': payload.get('zone'),
                        'message': payload.get('message'),
                        'timestamp': payload.get('timestamp')
                    }
                }
            )
    
    def _route_system(self, topic, payload):
        """Route system messages to WebSocket"""
        if "heartbeat" in topic:
            async_to_sync(self.channel_layer.group_send)(
                "device_health",
                {
                    'type': 'device_update',
                    'data': {
                        'node_id': payload.get('node_id'),
                        'node_name': payload.get('node_name'),
                        'status': payload.get('status'),
                        'battery': payload.get('battery'),
                        'timestamp': payload.get('timestamp')
                    }
                }
            )
        
        elif "status" in topic:
            async_to_sync(self.channel_layer.group_send)(
                "device_health",
                {
                    'type': 'device_update',
                    'data': {
                        'node_id': payload.get('node_id'),
                        'status': payload.get('status'),
                        'details': payload
                    }
                }
            )
    
    def _route_security(self, topic, payload):
        """Route security messages to WebSocket"""
        async_to_sync(self.channel_layer.group_send)(
            "security_alerts",
            {
                'type': 'security_alert',
                'severity': payload.get('severity', 'medium'),
                'data': {
                    'topic': topic,
                    'message': payload.get('message'),
                    'timestamp': payload.get('timestamp')
                }
            }
        )
    
    def start(self):
        """Start MQTT bridge connection"""
        try:
            if settings.MQTT_USER:
                self.client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
            
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            logger.info("MQTT Bridge started")
        except Exception as e:
            logger.error(f"Failed to start MQTT bridge: {e}")
    
    def stop(self):
        """Stop MQTT bridge connection"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT Bridge stopped")


# Singleton instance
mqtt_bridge = MQTTBridge()