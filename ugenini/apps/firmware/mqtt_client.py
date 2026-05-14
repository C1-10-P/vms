import paho.mqtt.client as mqtt
import json
import threading
import queue
import ssl
import time
import socket
import logging
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from typing import Dict, Callable, Any
from .mqtt_handlers import QRScanMQTTHandlers

logger = logging.getLogger(__name__)


class MQTTClientManager:
    """
    Singleton MQTT Client Manager for VMS
    Handles connection, subscription, and message routing
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
        
        self.client = None
        self.broker_host = getattr(settings, 'MQTT_BROKER', '192.168.8.104')
        self.broker_port = getattr(settings, 'MQTT_PORT', 1883)
        self.tls_port = getattr(settings, 'MQTT_TLS_PORT', 8883)
        self.username = getattr(settings, 'MQTT_USER', 'pusha')
        self.password = getattr(settings, 'MQTT_PASSWORD', 'pusha')
        self.keepalive = getattr(settings, 'MQTT_KEEPALIVE', 60)
        self._connected_flag = False
        self._initialized = True
        
        self.message_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        self.callback_thread = None
        
        self._register_handlers()
        self._initialized = True
    
    def _register_handlers(self):
        """Register message handlers for different topics"""
        self.handlers = {
            # Attendance topics
            'jkuat/attendance/class/sign_in': self._handle_attendance_checkin,
            'jkuat/attendance/class/sign_out': self._handle_attendance_checkout,
            'jkuat/attendance/class/alert': self._handle_attendance_alert,
            'jkuat/attendance/lab/sign_in': self._handle_lab_checkin,
            
            # Visitor topics
            'jkuat/visitor/tag/ping': self._handle_visitor_ping,
            'jkuat/visitor/tag/bind': self._handle_tag_bind,
            'jkuat/visitor/tag/unbind': self._handle_tag_unbind,
            'jkuat/visitor/tracking/+/+': self._handle_visitor_tracking,
            'jkuat/visitor/alert/zone_breach': self._handle_zone_breach,
            
            # System topics
            'jkuat/system/heartbeat/+': self._handle_heartbeat,
            'jkuat/system/status/+': self._handle_status,
            'jkuat/system/alert/+': self._handle_system_alert,
            'jkuat/system/config/+/response': self._handle_config_response,
            
            # Security topics
            'jkuat/security/access/request': self._handle_access_request,
            'jkuat/security/access/response/+': self._handle_access_response,
            'jkuat/security/geofence/breach': self._handle_geofence_breach,
            'jkuat/security/2fa/response': self._handle_2fa_response,

            # QR Scan handlers
        'jkuat/attendance/scan': QRScanMQTTHandlers.handle_attendance_scan,
        'jkuat/visitor/scan': QRScanMQTTHandlers.handle_visitor_scan,
        'jkuat/visitor/checkout': QRScanMQTTHandlers.handle_checkout_scan,
        }
    
    def connect(self, timeout=5):
        """Connect to MQTT broker with a timeout.

        Args:
            timeout (int): Maximum seconds to wait for connection acknowledgment.

        Returns:
            bool: True if connected and CONNACK received, False otherwise.
        """
        try:
            # Create a fresh client instance (ensures clean state)
            self.client = mqtt.Client(
                client_id=f"vms_backend_{timezone.now().timestamp()}",
                clean_session=True,
                protocol=mqtt.MQTTv311
            )

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            self.client.on_subscribe = self._on_subscribe

            # Authentication
            if self.username:
                self.client.username_pw_set(self.username, self.password)

            # TLS configuration
            if getattr(settings, 'MQTT_USE_TLS', False):
                self.client.tls_set(
                    ca_certs=getattr(settings, 'MQTT_CA_CERT', None),
                    certfile=getattr(settings, 'MQTT_CLIENT_CERT', None),
                    keyfile=getattr(settings, 'MQTT_CLIENT_KEY', None),
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLSv1_2
                )

            # Set a socket timeout to avoid indefinite blocking
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)

            try:
                # Attempt connection (this is blocking but will respect socket timeout)
                self.client.connect(self.broker_host, self.broker_port, self.keepalive)
            finally:
                socket.setdefaulttimeout(old_timeout)

            # Start network loop
            self.client.loop_start()

            # Wait for on_connect callback to set a flag or for timeout
            start = time.time()
            while not self._connected_flag and (time.time() - start) < timeout:
                time.sleep(0.1)

            if not self._connected_flag:
                logger.error(f"MQTT connection timeout after {timeout}s")
                self.client.loop_stop()
                self.client.disconnect()
                return False

            self.running = True

            # Start message processor thread
            self.worker_thread = threading.Thread(target=self._process_messages, daemon=True)
            self.worker_thread.start()

            logger.info(f"MQTT Client connected to {self.broker_host}:{self.broker_port}")
            return True

        except socket.timeout:
            logger.error(f"MQTT connection timed out (host={self.broker_host}, port={self.broker_port})")
            return False
        except ConnectionRefusedError:
            logger.error(f"MQTT connection refused – is the broker running on {self.broker_host}:{self.broker_port}?")
            return False
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.info("MQTT Client disconnected")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker"""
        if rc == 0:
            logger.info("MQTT connected successfully")
            self._connected_flag = True

            # Subscribe to all required topics
            topics = [
                ("jkuat/attendance/#", 1),
                ("jkuat/visitor/#", 1),
                ("jkuat/system/#", 1),
                ("jkuat/security/#", 1),
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to: {topic}")
        else:
            logger.error(f"MQTT connection failed with code: {rc}")
            self._connected_flag = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected"""
        logger.warning(f"MQTT disconnected with code: {rc}")
        # Attempt to reconnect
        if self.running:
            threading.Timer(5.0, self.connect).start()
    
    # def _on_message(self, client, userdata, msg):
    #     """Callback when message received"""
    #     try:
    #         payload = json.loads(msg.payload.decode('utf-8'))
    #         self.message_queue.put({
    #             'topic': msg.topic,
    #             'payload': payload,
    #             'qos': msg.qos,
    #             'timestamp': timezone.now().isoformat()
    #         })
    #         logger.debug(f"MQTT message received: {msg.topic}")
    #     except json.JSONDecodeError:
    #         logger.error(f"Invalid JSON payload on {msg.topic}: {msg.payload}")
    #     except Exception as e:
    #         logger.error(f"Error processing MQTT message: {e}")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received (robust version)"""
        try:
            raw = msg.payload.decode("utf-8", errors="ignore")

            # ================================
            # 1. SAFE JSON PARSING
            # ================================
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                # fallback for non-JSON payloads
                payload = {
                    "raw": raw
                }

            # ================================
            # 2. NORMALIZE DATA (CRITICAL)
            # ================================

            scan_value = (
                payload.get("data", {}).get("value")
                or payload.get("qr_data")
                or payload.get("tag")
                or payload.get("qr")
                or payload.get("raw")
            )

            method = payload.get("method")

            if not method:
                # auto-detect method
                if payload.get("tag"):
                    method = "rfid"
                elif payload.get("qr_data") or payload.get("qr"):
                    method = "qr"
                else:
                    method = "unknown"

            normalized_payload = {
                "node": payload.get("node", "unknown"),
                "type": payload.get("type", "scan"),
                "method": method,
                "value": scan_value,
                "raw": payload,
            }

            # ================================
            # 3. QUEUE MESSAGE
            # ================================
            self.message_queue.put({
                "topic": msg.topic,
                "payload": normalized_payload,
                "qos": msg.qos,
                "timestamp": timezone.now().isoformat()
            })

            logger.debug(f"MQTT message received: {msg.topic} | {method} | {scan_value}")

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback when message published"""
        logger.debug(f"MQTT message published: {mid}")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscribed"""
        logger.debug(f"MQTT subscribed: {mid}, QoS: {granted_qos}")
    
    def _process_messages(self):
        """Process messages from queue with handlers"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                
                # Find matching handler
                for pattern, handler in self.handlers.items():
                    if self._topic_matches(pattern, message['topic']):
                        try:
                            with transaction.atomic():
                                handler(message['topic'], message['payload'])
                        except Exception as e:
                            logger.error(f"Handler error for {message['topic']}: {e}")
                        break
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Message processor error: {e}")
    
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern with wildcards"""
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        if len(pattern_parts) != len(topic_parts):
            return False
        
        for p, t in zip(pattern_parts, topic_parts):
            if p != '+' and p != '#' and p != t:
                return False
            if p == '#':
                return True
        
        return True
    
    def publish(self, topic: str, payload: dict, qos: int = 1, retain: bool = False):
        """Publish message to MQTT broker"""
        try:
            message = json.dumps(payload)
            info = self.client.publish(topic, message, qos=qos, retain=retain)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to {topic}: {info.rc}")
            return info
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return None
    
    # ============ Message Handlers ============
    
    def _handle_attendance_checkin(self, topic, payload):
        """Handle attendance check-in from ESP32-CAM"""
        from apps.classroom.services import AttendanceService
        
        logger.info(f"Attendance check-in: {payload}")
        
        student_id = payload.get('student_id')
        class_code = payload.get('class_code')
        node_uuid = payload.get('node_uuid')
        method = payload.get('method', 'qr')
        
        # Process via service
        service = AttendanceService()
        result = service.process_api_check_in(student_id, class_code, node_uuid)
        
        # Send response
        if result.get('success'):
            self.publish(f"jkuat/attendance/class/status/{node_uuid}", {
                'status': 'success',
                'student_id': student_id,
                'message': 'Attendance recorded',
                'timestamp': timezone.now().isoformat()
            })
        else:
            self.publish(f"jkuat/attendance/class/status/{node_uuid}", {
                'status': 'failed',
                'student_id': student_id,
                'error': result.get('error'),
                'timestamp': timezone.now().isoformat()
            })
    
    def _handle_attendance_checkout(self, topic, payload):
        """Handle attendance check-out"""
        logger.info(f"Attendance check-out: {payload}")
        # Similar to check-in but for departure
    
    def _handle_attendance_alert(self, topic, payload):
        """Handle camera/scanning alerts"""
        logger.warning(f"Attendance alert: {payload}")
        
        node_uuid = payload.get('node_uuid')
        alert_type = payload.get('type')
        message = payload.get('message')
        
        # Store alert in database
        from apps.firmware.models import EdgeNode
        from apps.vms.models import VisitorAlert
        
        node = EdgeNode.objects.filter(node_uuid=node_uuid).first()
        if node:
            VisitorAlert.objects.create(
                alert_type='system',
                severity='medium' if alert_type == 'error' else 'low',
                message=f"Node {node.name}: {message}",
                data=payload
            )
    
    def _handle_lab_checkin(self, topic, payload):
        """Handle lab attendance check-in"""
        logger.info(f"Lab check-in: {payload}")
        # Similar to class attendance
    
    def _handle_visitor_ping(self, topic, payload):
        """Handle BLE tag ping from ESP32-C3"""
        from apps.vms.services import VisitorService
        
        logger.debug(f"Visitor ping: {payload}")
        
        tag_uuid = payload.get('tag_uuid')
        zone_code = payload.get('zone_code')
        node_uuid = payload.get('node_uuid')
        rssi = payload.get('rssi')
        
        # Process movement tracking
        service = VisitorService()
        result = service.track_visitor_movement(tag_uuid, zone_code, node_uuid, rssi)
        
        # Cache current location for real-time updates
        if result.get('success'):
            cache_key = f"visitor_location_{tag_uuid}"
            cache.set(cache_key, {
                'zone': result.get('zone'),
                'timestamp': timezone.now().isoformat()
            }, timeout=60)
    
    def _handle_tag_bind(self, topic, payload):
        """Handle tag assignment to visitor"""
        from apps.vms.models import BLETag, Visitor
        from apps.vms.services import VisitorService
        
        logger.info(f"Tag bind: {payload}")
        
        tag_uuid = payload.get('tag_uuid')
        visitor_id = payload.get('visitor_id')
        
        try:
            tag = BLETag.objects.get(tag_uuid=tag_uuid)
            visitor = Visitor.objects.get(id=visitor_id)
            
            tag.assign_to_visitor(visitor, None)
            
            self.publish(f"jkuat/visitor/tag/bind/response/{tag_uuid}", {
                'success': True,
                'visitor_id': visitor_id,
                'message': 'Tag assigned successfully'
            })
        except Exception as e:
            self.publish(f"jkuat/visitor/tag/bind/response/{tag_uuid}", {
                'success': False,
                'error': str(e)
            })
    
    def _handle_tag_unbind(self, topic, payload):
        """Handle tag release from visitor"""
        from apps.vms.models import BLETag
        
        logger.info(f"Tag unbind: {payload}")
        
        tag_uuid = payload.get('tag_uuid')
        
        try:
            tag = BLETag.objects.get(tag_uuid=tag_uuid)
            tag.release(None)
            
            self.publish(f"jkuat/visitor/tag/unbind/response/{tag_uuid}", {
                'success': True,
                'message': 'Tag released successfully'
            })
        except Exception as e:
            self.publish(f"jkuat/visitor/tag/unbind/response/{tag_uuid}", {
                'success': False,
                'error': str(e)
            })
    
    def _handle_visitor_tracking(self, topic, payload):
        """Handle visitor location tracking"""
        logger.debug(f"Visitor tracking: {topic} -> {payload}")
        # Already handled by _handle_visitor_ping
    
    def _handle_zone_breach(self, topic, payload):
        """Handle geofence zone breach alert"""
        from apps.vms.models import VisitorAlert
        
        logger.warning(f"Zone breach: {payload}")
        
        tag_uuid = payload.get('tag_uuid')
        zone_code = payload.get('zone_code')
        message = payload.get('message')
        
        VisitorAlert.objects.create(
            alert_type='zone_breach',
            severity='high',
            message=message,
            data=payload
        )
        
        # Notify security via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'security_alerts',
            {
                'type': 'security_alert',
                'severity': 'high',
                'data': {
                    'tag_uuid': tag_uuid,
                    'zone': zone_code,
                    'message': message,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
    def _handle_heartbeat(self, topic, payload):
        """Handle device heartbeat"""
        from apps.firmware.models import EdgeNode
        
        node_uuid = topic.split('/')[-1]
        logger.debug(f"Heartbeat from {node_uuid}: {payload}")
        
        try:
            node = EdgeNode.objects.get(node_uuid=node_uuid)
            node.update_heartbeat(payload)
        except EdgeNode.DoesNotExist:
            logger.warning(f"Heartbeat from unknown node: {node_uuid}")
    
    def _handle_status(self, topic, payload):
        """Handle device status update"""
        from apps.firmware.models import EdgeNode
        
        node_uuid = topic.split('/')[-1]
        logger.info(f"Status from {node_uuid}: {payload}")
        
        try:
            node = EdgeNode.objects.get(node_uuid=node_uuid)
            node.status = payload.get('status', node.status)
            node.firmware_version = payload.get('version', node.firmware_version)
            node.battery_level = payload.get('battery', node.battery_level)
            node.temperature = payload.get('temperature', node.temperature)
            node.save()
        except EdgeNode.DoesNotExist:
            logger.warning(f"Status from unknown node: {node_uuid}")
    
    def _handle_system_alert(self, topic, payload):
        """Handle system alerts from devices"""
        logger.error(f"System alert: {payload}")
        # Store alert and notify admins
    
    def _handle_config_response(self, topic, payload):
        """Handle configuration response from device"""
        logger.info(f"Config response: {payload}")
        # Store configuration acknowledgment
    
    def _handle_access_request(self, topic, payload):
        """Handle access request from RFID reader"""
        from apps.access.services import AccessControlService
        
        logger.info(f"Access request: {payload}")
        
        credential = payload.get('credential')
        zone_code = payload.get('zone_code')
        node_uuid = payload.get('node_uuid')
        
        service = AccessControlService()
        result = service.process_access_request(credential, zone_code, node_uuid)
        
        # Send response to device
        self.publish(f"jkuat/security/access/response/{node_uuid}", result)
    
    def _handle_access_response(self, topic, payload):
        """Handle access response from server (already handled)"""
        pass
    
    def _handle_geofence_breach(self, topic, payload):
        """Handle geofence breach alert"""
        logger.warning(f"Geofence breach: {payload}")
        # Similar to zone breach
    
    def _handle_2fa_response(self, topic, payload):
        """Handle 2FA verification response"""
        from apps.access.services import AccessControlService
        
        logger.info(f"2FA response: {payload}")
        
        session_token = payload.get('session_token')
        code = payload.get('code')
        
        result = AccessControlService.verify_2fa(session_token, code)
        
        if result.get('granted'):
            # Grant access
            self.publish(f"jkuat/security/access/granted/{session_token}", {
                'granted': True,
                'message': 'Access granted'
            })
        else:
            self.publish(f"jkuat/security/access/granted/{session_token}", {
                'granted': False,
                'message': result.get('message', 'Access denied')
            })


# Singleton instance
mqtt_client = MQTTClientManager()