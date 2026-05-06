from datetime import timezone

from pytz import timezone

import cv2
import base64
import logging
import requests
from django.conf import settings
from .camera_service import CameraQRScanner
from .ocr_service import ocr_service

logger = logging.getLogger(__name__)


class OCRCameraService:
    """
    Camera service with OCR integration for ID scanning
    Runs on Raspberry Pi and processes images locally or via API
    """
    
    def __init__(self):
        self.camera = CameraQRScanner()
        self.api_base = settings.VMS_API_URL if hasattr(settings, 'VMS_API_URL') else 'http://localhost:8000/api/v1'
    
    def scan_student_id_for_attendance(self, class_code=None):
        """
        Capture image of student ID and process with OCR for attendance
        """
        # Capture image
        frame = self.camera.capture_frame()
        if frame is None:
            return {'success': False, 'error': 'Camera capture failed'}
        
        # Convert to base64
        _, buffer = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Process locally or via API
        result = ocr_service.process_id_image(image_base64, 'student')
        
        if not result['success']:
            return result
        
        # Extract student registration
        student_reg = result['extracted_data'].get('registration_number')
        
        if not student_reg:
            return {'success': False, 'error': 'Could not extract registration number'}
        
        # Record attendance (local or API)
        from apps.classroom.services import AttendanceService
        service = AttendanceService()
        attendance_result = service.process_api_check_in(student_reg, class_code, 'raspberry_pi_ocr')
        
        # Save captured image for audit
        self._save_scan_image(frame, student_reg, 'attendance')
        
        return {
            'success': attendance_result.get('success', False),
            'student_reg': student_reg,
            'student_name': result['extracted_data'].get('full_name'),
            'class_code': class_code,
            'attendance': attendance_result,
            'confidence': result['confidence']
        }
    
    def scan_national_id_for_visitor(self):
        """
        Capture image of National ID and process with OCR for visitor check-in
        """
        frame = self.camera.capture_frame()
        if frame is None:
            return {'success': False, 'error': 'Camera capture failed'}
        
        _, buffer = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Process OCR
        result = ocr_service.process_id_image(image_base64, 'national')
        
        if not result['success']:
            return result
        
        extracted = result['extracted_data']
        
        # Check if visitor already exists
        from apps.core.models import Person
        person = None
        if extracted.get('id_number'):
            person = Person.objects.filter(national_id=extracted['id_number']).first()
        
        if person and person.person_type == 'visitor':
            # Existing visitor - check in
            from apps.vms.models import Visitor
            visitor = Visitor.objects.filter(person=person).first()
            if visitor:
                visitor.start_new_visit()
                self._save_scan_image(frame, extracted['id_number'], 'visitor_checkin')
                return {
                    'success': True,
                    'visitor_id': visitor.id,
                    'name': person.full_name,
                    'message': 'Visitor checked in successfully'
                }
        
        # New visitor - return extracted data for manual completion
        self._save_scan_image(frame, extracted.get('id_number', 'unknown'), 'visitor_scan')
        
        return {
            'success': False,
            'requires_manual_entry': True,
            'extracted_data': extracted,
            'message': 'New visitor. Please complete registration.'
        }
    
    def _save_scan_image(self, frame, identifier, scan_type):
        """Save captured image for audit"""
        from django.core.files.base import ContentFile
        
        _, buffer = cv2.imencode('.jpg', frame)
        image_data = ContentFile(buffer.tobytes())
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{scan_type}_{identifier}_{timestamp}.jpg"
        
        from django.core.files.storage import default_storage
        path = f"scans/{scan_type}/{filename}"
        default_storage.save(path, image_data)
        
        logger.info(f"Scan image saved: {path}")


# Singleton
ocr_camera = OCRCameraService()