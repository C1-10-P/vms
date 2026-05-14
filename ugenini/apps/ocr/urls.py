from django.urls import path
from . import views

app_name = 'ocr'

urlpatterns = [
    path('scanner/', views.scanner_page, name='scanner'),
    path('debug/', views.debug_ocr, name='debug'),
    path('debug/process/', views.debug_ocr_process, name='debug_process'),
]