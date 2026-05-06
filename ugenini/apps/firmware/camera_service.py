import cv2
import base64
import logging
from PIL import Image
import io
import pyzbar.pyzbar as pyzbar
from django.core.files.base import ContentFile
from django.utils import timezone
from threading import Lock

logger = logging.getLogger(__name__)


class CameraQRScanner:
    """
    Camera service for QR/Barcode scanning only
    No facial recognition - just QR codes and barcodes
    """
    
    _instance = None
    _camera = None
    _camera_lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.camera_id = 0
        self.is_initialized = False
        self._initialized = True
    
    def initialize_camera(self, camera_id=0, width=640, height=480):
        """Initialize the camera for scanning"""
        with self._camera_lock:
            if self._camera is not None:
                self.release_camera()
            
            self._camera = cv2.VideoCapture(camera_id)
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            if not self._camera.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return False
            
            self.is_initialized = True
            logger.info(f"Camera scanner initialized (ID: {camera_id})")
            return True
    
    def release_camera(self):
        """Release the camera"""
        if self._camera:
            self._camera.release()
            self._camera = None
        self.is_initialized = False
    
    def capture_frame(self):
        """Capture a single frame from camera"""
        if not self.is_initialized:
            logger.error("Camera not initialized")
            return None
        
        ret, frame = self._camera.read()
        if not ret:
            logger.error("Failed to capture frame")
            return None
        
        return frame
    
    def scan_qr_code(self, frame=None):
        """
        Scan for QR code in frame
        Returns decoded data if found, None otherwise
        """
        if frame is None:
            frame = self.capture_frame()
        
        if frame is None:
            return None
        
        # Convert to grayscale for better detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Decode QR codes and barcodes
        decoded_objects = pyzbar.decode(gray)
        
        if not decoded_objects:
            return None
        
        # Return the first detected code
        obj = decoded_objects[0]
        return {
            'data': obj.data.decode('utf-8'),
            'type': obj.type,  # QRCODE, CODE128, EAN13, etc.
            'raw_data': obj.data
        }
    
    def scan_student_id(self):
        """
        Scan student ID QR code and process attendance
        Expected QR format: STUDENT_REG_NUMBER|CLASS_CODE
        Example: "ENE221-0108/2018|TIE4101"
        """
        frame = self.capture_frame()
        if frame is None:
            return {'success': False, 'error': 'Camera capture failed'}
        
        # Scan for QR code
        scan_result = self.scan_qr_code(frame)
        
        if not scan_result:
            return {'success': False, 'error': 'No QR code detected'}
        
        # Parse QR data
        qr_data = scan_result['data']
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
        result = service.process_api_check_in(student_reg, class_code, 'raspberry_pi_camera')
        
        # Save captured image for audit trail
        if result.get('success'):
            self._save_scan_image(frame, student_reg, 'attendance')
        
        return result
    
    def scan_visitor_qr(self):
        """
        Scan visitor QR code for check-in/check-out
        Expected QR format: JSON with visitor data or simple token
        """
        frame = self.capture_frame()
        if frame is None:
            return {'success': False, 'error': 'Camera capture failed'}
        
        # Scan for QR code
        scan_result = self.scan_qr_code(frame)
        
        if not scan_result:
            return {'success': False, 'error': 'No QR code detected'}
        
        qr_data = scan_result['data']
        
        # Try to parse as JSON (pre-registered visitor)
        import json
        try:
            visitor_data = json.loads(qr_data)
            
            from apps.vms.services import VisitorService
            service = VisitorService()
            result = service.process_visitor_checkin(visitor_data)
            
            if result.get('success'):
                self._save_scan_image(frame, visitor_data.get('national_id', 'visitor'), 'visitor')
            
            return result
            
        except json.JSONDecodeError:
            # QR contains just a visitor ID or tag ID
            # This could be for check-out
            from apps.vms.models import BLETag, Visitor
            
            # Check if it's a tag UUID
            tag = BLETag.objects.filter(tag_uuid=qr_data).first()
            if tag:
                from apps.vms.services import VisitorService
                service = VisitorService()
                result = service.process_visitor_checkout(tag)
                return result
            
            # Check if it's a visitor ID
            visitor = Visitor.objects.filter(id=qr_data).first()
            if visitor:
                return {
                    'success': True,
                    'visitor_id': visitor.id,
                    'name': visitor.person.full_name,
                    'message': 'Visitor found. Please proceed to check-in.'
                }
            
            return {'success': False, 'error': 'Invalid QR code format'}
    
    def scan_barcode(self):
        """Scan barcode (for student ID cards with barcodes)"""
        frame = self.capture_frame()
        if frame is None:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded_objects = pyzbar.decode(gray)
        
        if not decoded_objects:
            return None
        
        obj = decoded_objects[0]
        return {
            'data': obj.data.decode('utf-8'),
            'type': obj.type
        }
    
    def _save_scan_image(self, frame, identifier, scan_type):
        """Save captured image for audit trail"""
        _, buffer = cv2.imencode('.jpg', frame)
        image_data = ContentFile(buffer.tobytes())
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{scan_type}_{identifier}_{timestamp}.jpg"
        
        from django.core.files.storage import default_storage
        path = f"scans/{scan_type}/{filename}"
        default_storage.save(path, image_data)
        
        logger.info(f"Scan image saved: {path}")
    
    def continuous_scan_mode(self, callback, scan_type='attendance'):
        """
        Run continuous scanning mode
        callback will be called with scan results
        """
        if not self.initialize_camera():
            logger.error("Failed to initialize camera for continuous scan")
            return
        
        logger.info(f"Starting continuous scan mode for {scan_type}")
        
        try:
            while True:
                frame = self.capture_frame()
                if frame is None:
                    continue
                
                scan_result = self.scan_qr_code(frame)
                
                if scan_result:
                    logger.info(f"QR detected: {scan_result['data']}")
                    
                    if scan_type == 'attendance':
                        result = self.process_attendance_scan_frame(frame, scan_result)
                    elif scan_type == 'visitor':
                        result = self.process_visitor_scan_frame(frame, scan_result)
                    else:
                        result = {'data': scan_result['data'], 'type': scan_result['type']}
                    
                    callback(result)
                    
                    # Wait a bit to avoid multiple scans
                    import time
                    time.sleep(2)
                
        except KeyboardInterrupt:
            logger.info("Continuous scan stopped")
        finally:
            self.release_camera()
    
    def process_attendance_scan_frame(self, frame, scan_result):
        """Process attendance from scanned frame"""
        qr_data = scan_result['data']
        parts = qr_data.split('|')
        
        if len(parts) >= 2:
            student_reg = parts[0].strip()
            class_code = parts[1].strip()
        else:
            student_reg = qr_data.strip()
            class_code = None
        
        from apps.classroom.services import AttendanceService
        service = AttendanceService()
        result = service.process_api_check_in(student_reg, class_code, 'raspberry_pi_camera')
        
        if result.get('success'):
            self._save_scan_image(frame, student_reg, 'attendance')
        
        return result
    
    def process_visitor_scan_frame(self, frame, scan_result):
        """Process visitor from scanned frame"""
        qr_data = scan_result['data']
        
        import json
        try:
            visitor_data = json.loads(qr_data)
            
            from apps.vms.services import VisitorService
            service = VisitorService()
            result = service.process_visitor_checkin(visitor_data)
            
            if result.get('success'):
                self._save_scan_image(frame, visitor_data.get('national_id', 'visitor'), 'visitor')
            
            return result
            
        except json.JSONDecodeError:
            return {'success': False, 'error': 'Invalid QR format'}


# Singleton instance
camera_scanner = CameraQRScanner()