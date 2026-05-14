from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.base import ContentFile
from django.utils import timezone
import base64
import json

from apps.firmware.ocr_service import ocr_service
from apps.classroom.services import AttendanceService
from apps.vms.services import VisitorService
from apps.core.models import Student, Visitor, Person


class OCRProcessIDView(APIView):
    """
    API endpoint for processing ID images via OCR
    Accepts image upload or base64 image data
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):

        image = request.data.get('image_base64')

        class_code = request.data.get('class_code')

        engine = request.data.get('engine', 'easyocr')

        debug = request.data.get('debug', False)

        if not image:
            return Response(
                {'error': 'Image required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process OCR
        result = ocr_service.process_id_image(
            image,
            'student',
            engine
        )

        if not result['success']:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optional confidence validation
        if result.get('confidence', 0) < 40:
            return Response({
                'success': False,
                'error': 'Image quality too low. Please retake the photo.',
                'confidence': result.get('confidence', 0),
                'raw_text': result.get('raw_text', '')
            }, status=status.HTTP_400_BAD_REQUEST)

        # Debug mode
        if debug:
            result['debug'] = {
                'raw_text': result.get('raw_text'),
                'detected_type': result.get('id_type'),
                'confidence': result.get('confidence')
            }

        # Get registration number
        student_reg = result['extracted_data'].get(
            'registration_number'
        )

        if not student_reg:
            return Response({
                'success': False,
                'error': 'Could not extract registration number from ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Record attendance
        service = AttendanceService()

        attendance_result = service.process_api_check_in(
            student_reg,
            class_code,
            'ocr_scanner'
        )

        return Response({
            'success': attendance_result.get('success', False),
            'student': result['extracted_data'],
            'attendance': attendance_result,
            'confidence': result['confidence'],
            'debug': result.get('debug')
        })
    
    def _process_attendance(self, extracted_data):
        """Process attendance using extracted student data"""
        student_reg = extracted_data.get('registration_number')
        if not student_reg:
            return {'success': False, 'error': 'No registration number found in ID'}
        
        # Get class code from request or use default
        class_code = self.request.data.get('class_code')
        
        service = AttendanceService()
        result = service.process_api_check_in(student_reg, class_code, 'ocr_scanner')
        
        return result
    
    def _process_visitor_checkin(self, extracted_data):
        """Process visitor check-in using extracted ID data"""
        id_number = extracted_data.get('id_number')
        first_name = extracted_data.get('first_name')
        last_name = extracted_data.get('last_name')
        
        if not id_number:
            return {'success': False, 'error': 'No ID number found in image'}
        
        # Build visitor data
        visitor_data = {
            'first_name': first_name or 'Unknown',
            'last_name': last_name or 'Visitor',
            'national_id': id_number,
            'phone_number': self.request.data.get('phone_number', ''),
            'email': self.request.data.get('email', ''),
            'organization': self.request.data.get('organization', ''),
            'purpose': self.request.data.get('purpose', 'meeting'),
            'host_email': self.request.data.get('host_email', '')
        }
        
        service = VisitorService()
        result = service.process_visitor_checkin(visitor_data)
        
        return result


class OCRScanAttendanceView(APIView):
    """
    Simplified endpoint for scanning student ID and recording attendance
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        image = request.data.get('image_base64')
        class_code = request.data.get('class_code')
        
        if not image:
            return Response({'error': 'Image required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process OCR
        result = ocr_service.process_id_image(image, 'student')
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        # Get registration number
        student_reg = result['extracted_data'].get('registration_number')
        
        if not student_reg:
            return Response({
                'success': False,
                'error': 'Could not extract registration number from ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Record attendance
        service = AttendanceService()
        attendance_result = service.process_api_check_in(student_reg, class_code, 'ocr_scanner')
        
        return Response({
            'success': attendance_result.get('success', False),
            'student': result['extracted_data'],
            'attendance': attendance_result,
            'confidence': result['confidence']
        })


class OCRScanVisitorView(APIView):
    """
    Endpoint for scanning visitor ID and checking in
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):

        image = request.data.get('image_base64')

        engine = request.data.get('engine', 'easyocr')

        debug = request.data.get('debug', False)

        if not image:
            return Response(
                {'error': 'Image required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process OCR
        result = ocr_service.process_id_image(
            image,
            'auto',
            engine
        )

        if not result['success']:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optional confidence validation
        if result.get('confidence', 0) < 40:
            return Response({
                'success': False,
                'error': 'Image quality too low. Please retake the photo.',
                'confidence': result.get('confidence', 0),
                'raw_text': result.get('raw_text', '')
            }, status=status.HTTP_400_BAD_REQUEST)

        # Debug mode
        if debug:
            result['debug'] = {
                'raw_text': result.get('raw_text'),
                'detected_type': result.get('id_type'),
                'confidence': result.get('confidence')
            }

        # Check if person exists
        id_number = result['extracted_data'].get('id_number')
        person = None

        if id_number:
            person = Person.objects.filter(
                national_id=id_number
            ).first()

        if person and person.person_type == 'visitor':

            visitor = Visitor.objects.filter(
                person=person
            ).first()

            if visitor:
                # service = VisitorService()
                # result = service.process_visitor_checkin()
                visitor.start_new_visit()

                return Response({
                    'success': True,
                    'visitor_id': visitor.id,
                    'name': person.full_name,
                    'message': 'Welcome back! Check-in successful.',
                    'debug': result.get('debug')
                })

        # New visitor
        return Response({
            'success': False,
            'requires_manual_entry': True,
            'extracted_data': result['extracted_data'],
            'message': 'Please provide additional visitor information',
            'debug': result.get('debug')
        }, status=status.HTTP_202_ACCEPTED)