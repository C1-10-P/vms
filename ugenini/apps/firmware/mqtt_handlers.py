import json
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class QRScanMQTTHandlers:
    """
    MQTT handlers for QR scan messages from ESP32-CAM
    """
    
    @staticmethod
    def handle_attendance_scan(topic, payload):
        """Handle attendance QR scan from ESP32-CAM"""
        logger.info(f"Attendance QR scan received from {topic}")
        
        node_uuid = payload.get('node_uuid')
        qr_data = payload.get('qr_data')
        
        if not qr_data:
            logger.error("No QR data in payload")
            return
        
        # Parse QR data (format: STUDENT_REG|CLASS_CODE)
        parts = qr_data.split('|')
        
        if len(parts) >= 2:
            student_reg = parts[0].strip()
            class_code = parts[1].strip()
        else:
            student_reg = qr_data.strip()
            class_code = None
        
        # Process attendance
        from apps.classroom.services import AttendanceService
        service = AttendanceService()
        result = service.process_api_check_in(student_reg, class_code, node_uuid)
        
        # Send response back to device
        from apps.firmware.mqtt_client import mqtt_client
        mqtt_client.publish(f"jkuat/attendance/scan/response/{node_uuid}", {
            'success': result.get('success', False),
            'student_reg': student_reg,
            'class_code': class_code,
            'message': result.get('message', result.get('error', '')),
            'timestamp': timezone.now().isoformat()
        })
        
        logger.info(f"Attendance scan result: {result}")
    
    @staticmethod
    def handle_visitor_scan(topic, payload):
        """Handle visitor QR scan from ESP32-CAM"""
        logger.info(f"Visitor QR scan received from {topic}")
        
        node_uuid = payload.get('node_uuid')
        qr_data = payload.get('qr_data')
        
        if not qr_data:
            logger.error("No QR data in payload")
            return
        
        # Parse QR data (JSON format)
        import json
        try:
            visitor_data = json.loads(qr_data)
            
            from apps.vms.services import VisitorService
            service = VisitorService()
            result = service.process_visitor_checkin(visitor_data)
            
            # Send response back to device
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f"jkuat/visitor/scan/response/{node_uuid}", {
                'success': result.get('success', False),
                'visitor_id': result.get('visitor_id'),
                'tag_id': result.get('tag_id'),
                'message': result.get('message', result.get('error', '')),
                'timestamp': timezone.now().isoformat()
            })
            
            logger.info(f"Visitor scan result: {result}")
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in QR data: {qr_data}")
            
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f"jkuat/visitor/scan/response/{node_uuid}", {
                'success': False,
                'error': 'Invalid QR code format',
                'timestamp': timezone.now().isoformat()
            })
    
    @staticmethod
    def handle_checkout_scan(topic, payload):
        """Handle visitor check-out QR scan"""
        logger.info(f"Checkout QR scan received from {topic}")
        
        node_uuid = payload.get('node_uuid')
        qr_data = payload.get('qr_data')
        
        if not qr_data:
            logger.error("No QR data in payload")
            return
        
        from apps.vms.models import BLETag
        
        # Try to find tag by UUID
        tag = BLETag.objects.filter(tag_uuid=qr_data).first()
        
        if tag:
            from apps.vms.services import VisitorService
            service = VisitorService()
            result = service.process_visitor_checkout(tag)
            
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f"jkuat/visitor/checkout/response/{node_uuid}", {
                'success': result.get('success', False),
                'visitor_id': result.get('visitor_id'),
                'message': result.get('message', result.get('error', '')),
                'timestamp': timezone.now().isoformat()
            })
        else:
            from apps.firmware.mqtt_client import mqtt_client
            mqtt_client.publish(f"jkuat/visitor/checkout/response/{node_uuid}", {
                'success': False,
                'error': 'Tag not found',
                'timestamp': timezone.now().isoformat()
            })