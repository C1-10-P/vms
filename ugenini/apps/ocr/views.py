from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.firmware.ocr_service import ocr_service
import base64
import cv2
import numpy as np

@login_required
def scanner_page(request):
    return render(request, 'ocr/scanner.html')

@login_required
def debug_ocr(request):
    return render(request, 'ocr/debug.html')

@login_required
def debug_ocr_process(request):
    if request.method == 'POST':
        image_data = request.POST.get('image_base64')
        engine = request.POST.get('engine', 'easyocr')
        if not image_data:
            return JsonResponse({'error': 'No image provided'}, status=400)
        # Decode base64
        img_bytes = base64.b64decode(image_data.split(',')[1])
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Use OCR service
        text, details = ocr_service.extract_text(img, engine=engine)
        # Also try to extract structured fields
        structured = ocr_service.extract_student_id_info(text)
        if not structured.id_number and not structured.full_name:
            structured = ocr_service.extract_national_id_info(text)

        return JsonResponse({
            'success': True,
            'raw_text': text,
            'details': details,  # list of [bbox, text, confidence]
            'structured': {
                'full_name': structured.full_name,
                'id_number': structured.id_number,
                'registration_number': structured.registration_number,
                'date_of_birth': structured.date_of_birth,
            },
            'engine_used': engine
        })
    return JsonResponse({'error': 'Invalid method'}, status=405)