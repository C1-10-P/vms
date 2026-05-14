import cv2
import numpy as np
import re
import logging
import base64
import io
from PIL import Image
import pytesseract
from pytesseract import Output
from django.core.files.base import ContentFile
from django.utils import timezone
from django.core.cache import cache
import easyocr  # Alternative OCR engine
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

# Configure Tesseract path (adjust based on your OS)
# Windows: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Linux: '/usr/bin/tesseract'
# import platform
# if platform.system() == 'Windows':
#     pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# else:
#     pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


@dataclass
class ExtractedData:
    """Data structure for extracted ID information"""
    id_type: str  # 'student', 'national', 'visitor'
    id_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    registration_number: Optional[str] = None
    class_code: Optional[str] = None
    department: Optional[str] = None
    institution: Optional[str] = None
    expiry_date: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0


class OCRService:
    """
    Complete OCR service for Student ID and National ID scanning
    Supports both Tesseract and EasyOCR engines
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Initialize OCR engines
        self.use_easyocr = False
        try:
            self.reader = easyocr.Reader(['en'])  # EasyOCR for better accuracy
            self.use_easyocr = True
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.warning(f"EasyOCR not available, using Tesseract: {e}")
            self.reader = None
        
        self._initialized = True
    
    # ============ Image Preprocessing ============
    
    def preprocess_image(self, image):
        """
        Preprocess image for better OCR accuracy
        Steps: Grayscale → Denoise → Threshold → Deskew
        """
        if isinstance(image, str):
            # Base64 image
            image_data = base64.b64decode(image)
            np_arr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        elif isinstance(image, bytes):
            np_arr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        elif isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Upscale image for OCR
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Bilateral filter preserves text edges
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # Sharpen image
        kernel = np.array([
                [-1,-1,-1],
                [-1, 9,-1],
                [-1,-1,-1]
        ])

        sharpened = cv2.filter2D(gray, -1, kernel)

        # Adaptive threshold handles uneven lighting
        thresh = cv2.adaptiveThreshold(
            sharpened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            2
        )
        
        # Deskew (correct image rotation)
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if angle != 0:
            (h, w) = thresh.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return thresh, img
    
    def _normalize_text(self, text: str) -> str:

        text = text.upper()

        replacements = {
            ':': ' ',
            ';': ' ',
            '|': ' ',
            ',': ' ',
            '\n': ' ',
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        text = re.sub(r'\s+', ' ', text)

        return text.strip()
    
    def crop_top_region(self, image):

        if isinstance(image, str):
            image_data = base64.b64decode(image)
            np_arr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        elif isinstance(image, bytes):
            np_arr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        elif isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        else:
            img = image

        h, w = img.shape[:2]

        # Keep only upper 45% of ID
        top_crop = img[0:int(h * 0.45), :]

        return top_crop
    
    # ============ Text Extraction ============
    
    def extract_text_tesseract(self, image, preprocessing=True):
        """Extract text using Tesseract OCR"""
        if preprocessing:
            processed_img, original = self.preprocess_image(image)
            img_to_ocr = processed_img
        else:
            if isinstance(image, str):
                image_data = base64.b64decode(image)
                np_arr = np.frombuffer(image_data, np.uint8)
                img_to_ocr = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
            else:
                img_to_ocr = image
        
        # Configure Tesseract for ID card recognition
        custom_config = (
                            r'--oem 3 '
                            r'--psm 4 '
                            r'-c tessedit_char_whitelist='
                            r'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/- '
                        )
        
        text = pytesseract.image_to_string(img_to_ocr, config=custom_config)
        
        # Get detailed data
        data = pytesseract.image_to_data(img_to_ocr, output_type=Output.DICT, config=custom_config)
        
        return text, data
    
    def extract_text_easyocr(self, image, preprocessing=True):
        """Extract text using EasyOCR (more accurate for ID cards)"""
        if preprocessing:
            processed_img, original = self.preprocess_image(image)
            img_to_ocr = processed_img
        else:
            if isinstance(image, str):
                image_data = base64.b64decode(image)
                np_arr = np.frombuffer(image_data, np.uint8)
                img_to_ocr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            else:
                img_to_ocr = image
        
        results = self.reader.readtext(img_to_ocr)
        
        # Combine results into text
        text = ' '.join([result[1] for result in results])
        
        # Create detailed data structure
        data = {
            'text': text,
            'boxes': [result[0] for result in results],
            'texts': [result[1] for result in results],
            'confidences': [result[2] for result in results]
        }
        
        return text, data
    
    def extract_text(self, image, engine='auto'):
        """Extract text using best available engine"""
        if engine == 'easyocr' and self.use_easyocr:
            return self.extract_text_easyocr(image)
        elif engine == 'tesseract':
            return self.extract_text_tesseract(image)
        else:  # auto
            if self.use_easyocr:
                return self.extract_text_easyocr(image)
            else:
                return self.extract_text_tesseract(image)
    
    # ============ ID-Specific Extraction ============
    
    def extract_student_id_info(self, text: str) -> ExtractedData:
        """
        Extract student information from OCR text
        Patterns for Kenyan university student IDs
        """
        data = ExtractedData(id_type='student')
        data.raw_text = text
        
        # Patterns for Kenyan student IDs
        patterns = {
            # Registration number: ENE221-0108/2018, SCT211-001/2020, etc.
            'registration': r'([A-Z]{3,4}\d{3}-\d{4}/\d{4})',
            
            # Name patterns: "Name: John Doe" or "John Doe"
            'name': r'(?:Name|Student Name|Full Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            
            # Course/Program
            'program': r'(?:Program|Course|Degree)[:\s]+([A-Z][a-zA-Z\s]+(?:Engineering|Science|Technology|Business))',
            
            # Year of study
            'year': r'(?:Year|Year of Study)[:\s]+(\d+)',
            
            # Department
            'department': r'(?:Department|Dept)[:\s]+([A-Z][a-zA-Z\s]+(?:Engineering|Science))',
            
            # Institution
            'institution': r'(?:University|Institution|School)[:\s]+([A-Z][a-zA-Z\s]+University)',
            
            # Date of birth
            'dob': r'(?:DOB|Date of Birth|Birth Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        }
        
        # Extract using regex
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key == 'registration':
                    data.registration_number = value
                    data.id_number = value
                elif key == 'name':
                    data.full_name = value
                    name_parts = value.split()
                    if len(name_parts) >= 2:
                        data.first_name = name_parts[0]
                        data.last_name = ' '.join(name_parts[1:])
                elif key == 'program':
                    data.class_code = value
                elif key == 'year':
                    pass
                elif key == 'department':
                    data.department = value
                elif key == 'institution':
                    data.institution = value
                elif key == 'dob':
                    data.date_of_birth = value
        
        # Additional name extraction if not found
        if not data.full_name:
            # Look for two consecutive capitalized words
            name_match = re.search(r'([A-Z][a-z]+)\s+([A-Z][a-z]+)', text)
            if name_match:
                data.first_name = name_match.group(1)
                data.last_name = name_match.group(2)
                data.full_name = f"{data.first_name} {data.last_name}"
        
        return data
    
    def extract_national_id_info(self, text: str) -> ExtractedData:

        data = ExtractedData(id_type='national')

        text = self._normalize_text(text)

        data.raw_text = text

        # ==========================================
        # ID NUMBER
        # ==========================================

        id_patterns = [
            r'ID NUMBER\s+(\d{7,8})',
            r'ID NO\s+(\d{7,8})',
            r'\b(\d{7,8})\b'
        ]

        for pattern in id_patterns:
            match = re.search(pattern, text)
            if match:
                data.id_number = match.group(1)
                break

        # ==========================================
        # FULL NAMES
        # ==========================================

        name_patterns = [
            r'FULL NAMES\s+([A-Z\s]{5,50})',
            r'NAMES\s+([A-Z\s]{5,50})'
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text)

            if match:

                name = match.group(1).strip()

                # Remove accidental extra labels
                stop_words = [
                    'DATE',
                    'SEX',
                    'PLACE',
                    'BIRTH'
                ]

                for stop in stop_words:
                    if stop in name:
                        name = name.split(stop)[0].strip()

                data.full_name = name.title()

                parts = data.full_name.split()

                if len(parts) >= 2:
                    data.first_name = parts[0]
                    data.last_name = " ".join(parts[1:])

                break

        return data
    
    def extract_visitor_info(self, text: str) -> ExtractedData:
        """
        Extract visitor information from ID
        """
        data = ExtractedData(id_type='visitor')
        data.raw_text = text
        
        # Try national ID extraction first
        national_data = self.extract_national_id_info(text)
        if national_data.id_number:
            return national_data
        
        # Fallback to general extraction
        # Look for any 8-digit number as potential ID
        id_match = re.search(r'\b(\d{8})\b', text)
        if id_match:
            data.id_number = id_match.group(1)
        
        # Look for phone number
        phone_match = re.search(r'(?:\+254|0)?(\d{9})', text)
        if phone_match:
            data.id_number = phone_match.group(1)
        
        # Extract name
        name_match = re.search(r'([A-Z][a-z]+)\s+([A-Z][a-z]+)', text)
        if name_match:
            data.first_name = name_match.group(1)
            data.last_name = name_match.group(2)
            data.full_name = f"{data.first_name} {data.last_name}"
        
        return data
    
    # ============ Complete Processing Pipeline ============
    
    def process_id_image(self, image, id_type='auto', engine='auto') -> Dict:
        """
        Complete pipeline: Process ID image and extract information
        """
        try:
            # Step 1: Extract text from image
            extracted_text, ocr_data = self.extract_text(image, engine)
            extracted_text = self._normalize_text(extracted_text)
            
            if not extracted_text or len(extracted_text.strip()) < 5:
                return {
                    'success': False,
                    'error': 'No text detected in image. Please ensure the ID is clear and well-lit.',
                    'ocr_confidence': 0
                }
            
            # Step 2: Determine ID type if auto
            detected_type = id_type
            if id_type == 'auto':

                # Crop only top region of card
                top_region = self.crop_top_region(image)

                # OCR top region only
                top_text, _ = self.extract_text(top_region, engine)

                # Normalize OCR text
                top_text = self._normalize_text(top_text)

                # Detect type using top section
                detected_type = self._detect_id_type(top_text)
            
            # Step 3: Extract structured data based on type
            if detected_type == 'student':
                extracted_data = self.extract_student_id_info(extracted_text)
            elif detected_type == 'national':
                extracted_data = self.extract_national_id_info(extracted_text)
            else:
                extracted_data = self.extract_visitor_info(extracted_text)
            
            # Step 4: Calculate confidence score
            confidence = self._calculate_confidence(extracted_data, ocr_data)
            
            # Step 5: Validate extracted data against database
            validation = self._validate_extracted_data(extracted_data, detected_type)
            
            return {
                'success': True,
                'id_type': detected_type,
                'extracted_data': {
                    'id_number': extracted_data.id_number,
                    'first_name': extracted_data.first_name,
                    'last_name': extracted_data.last_name,
                    'full_name': extracted_data.full_name,
                    'registration_number': extracted_data.registration_number,
                    'date_of_birth': extracted_data.date_of_birth,
                    'department': extracted_data.department,
                    'institution': extracted_data.institution,
                },
                'raw_text': extracted_text[:500],
                'confidence': confidence,
                'validation': validation,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def _detect_id_type(self, text: str) -> str:

        text = self._normalize_text(text)

        student_score = 0
        national_score = 0

        # ==========================================
        # STUDENT ID DETECTION
        # ==========================================

        student_patterns = [
            r'[A-Z]{2,5}\d{2,5}/\d{4}',
            r'[A-Z]{3,4}\d{3}-\d{4}/\d{4}'
        ]

        for pattern in student_patterns:
            if re.search(pattern, text):
                student_score += 5

        student_keywords = [
            'REGISTRATION',
            'ADMISSION',
            'STUDENT IDENTIFICATION CARD',
            'UNIVERSITY',
            'VALID'
        ]

        for word in student_keywords:
            if word in text:
                student_score += 2

        # ==========================================
        # KENYAN NATIONAL ID
        # ==========================================

        national_keywords = [
            'SERIAL NUMBER',
            'ID NUMBER',
            'FULL NAMES',
            'REPUBLIC OF KENYA',
            'JAMHURI YA KENYA',
        ]

        for word in national_keywords:
            if word in text:
                national_score += 3

        # Kenyan ID number
        if re.search(r'\b\d{7,8}\b', text):
            national_score += 4

        # ==========================================
        # TOP REGION PRIORITY
        # ==========================================

        lines = text.split()

        top_region = " ".join(lines[:30])

        top_keywords = [
            'SERIAL NUMBER',
            'ID NUMBER',
            'FULL NAMES'
        ]

        for word in top_keywords:
            if word in top_region:
                national_score += 5

        # ==========================================
        # DECISION
        # ==========================================

        if national_score >= student_score and national_score >= 7:
            return 'national'

        if student_score > national_score and student_score >= 5:
            return 'student'

        return 'visitor'
    
    def _calculate_confidence(self, extracted_data: ExtractedData, ocr_data) -> float:
        """Calculate confidence score for extraction"""
        confidence = 0.0
        total_fields = 0
        
        # Check extracted fields
        if extracted_data.id_number:
            confidence += 25
            total_fields += 1
        if extracted_data.first_name:
            confidence += 25
            total_fields += 1
        if extracted_data.last_name:
            confidence += 25
            total_fields += 1
        if extracted_data.full_name:
            confidence += 25
            total_fields += 1
        
        if total_fields > 0:
            confidence = (confidence / total_fields) if total_fields > 0 else 0
        
        return min(confidence, 100)
    
    def _validate_extracted_data(self, data: ExtractedData, id_type: str) -> Dict:
        """Validate extracted data against database"""
        validation = {
            'student_exists': False,
            'visitor_exists': False,
            'needs_manual_review': False,
            'existing_record': None
        }
        
        from apps.core.models import Student, Visitor, Person
        
        # Check if student exists
        if data.registration_number:
            student = Student.objects.filter(
                student_reg_number=data.registration_number,
                is_active=True
            ).select_related('person').first()
            
            if student:
                validation['student_exists'] = True
                validation['existing_record'] = {
                    'id': student.id,
                    'name': student.person.full_name,
                    'reg_number': student.student_reg_number
                }
        
        # Check if person exists by ID
        if data.id_number:
            person = Person.objects.filter(national_id=data.id_number).first()
            if person:
                validation['existing_record'] = {
                    'id': person.id,
                    'name': person.full_name,
                    'type': person.person_type
                }
        
        # Check if manual review needed (low confidence)
        if data.id_number and not validation['existing_record']:
            validation['needs_manual_review'] = True
        
        return validation


# Singleton instance
ocr_service = OCRService()