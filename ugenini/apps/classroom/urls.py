from django.urls import path
from apps.classroom import views_session
from . import views


app_name = 'classroom'

urlpatterns = [
    #  Main Views 
    path('', views.AttendanceListView.as_view(), name='list'),
    path('check-in/', views.AttendanceCheckInView.as_view(), name='check_in'),
    path('api/students/', views.api_students, name='api_students'),
    # path('<int:pk>/', views.AttendanceDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.AttendanceUpdateView.as_view(), name='edit'),
    path('<int:pk>/verify/', views.AttendanceVerifyView.as_view(), name='verify'),
    
    #  Reports 
    path('reports/', views.AttendanceReportView.as_view(), name='report'),
    path('reports/daily/', views.daily_attendance_report, name='daily_report'),
    path('reports/weekly/', views.weekly_attendance_report, name='weekly_report'),
    path('reports/monthly/', views.monthly_attendance_report, name='monthly_report'),
    path('reports/student/<int:student_id>/', views.student_attendance_report, name='student_report'),
    
    #  Exports 
    path('export/csv/', views.export_attendance_csv, name='export_csv'),
    # path('export/excel/', views.export_attendance_excel, name='export_excel'),
    path('export/pdf/', views.export_attendance_pdf, name='export_pdf'),

    # Import/Export URLs - these work with the updated service; check file to change urls appropriatelly
    
    # path('import/', views.AttendanceImportView.as_view(), name='attendance_import'),
    # path('download-template/', views.download_attendance_template, name='download_template'),
    # path('export/', views.export_attendance_records, name='attendance_export'),

    path('attendance/export/', views.export_attendance_excel, name='export_attendance'),
    path('attendance/import/', views.import_attendance_excel, name='import_attendance'),
    path('attendance/template/', views.download_attendance_template, name='attendance_template'),
    
    #  API Endpoints for ESP32 
    path('api/check-in/', views.api_attendance_checkin, name='api_check_in'),
    path('api/verify/', views.api_verify_attendance, name='api_verify'),
    path('api/bulk/', views.api_bulk_attendance, name='api_bulk'),
    
    #  AJAX Endpoints 
    path('ajax/search-students/', views.ajax_search_students, name='ajax_search_students'),
    path('ajax/get-class-schedule/', views.ajax_get_class_schedule, name='ajax_get_class_schedule'),
    path('ajax/recent-activity/', views.ajax_recent_activity, name='ajax_recent_activity'),
    
    #  Statistics 
    path('stats/summary/', views.attendance_summary, name='summary'),
    path('stats/trends/', views.attendance_trends, name='trends'),
    path('stats/by-course/', views.attendance_by_course, name='by_course'),

    # Session URLs
    path('sessions/', views_session.AttendanceSessionListView.as_view(), name='session_list'),
    path('sessions/create/', views_session.AttendanceSessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/', views_session.AttendanceSessionDetailView.as_view(), name='session_detail'),
    path('sessions/validate/<str:session_id>/', views_session.AttendanceSessionValidateView.as_view(), name='session_validate'),
    path('sessions/<int:pk>/detail-json/', views_session.get_session_detail_json, name='session_detail_json'),
    path('quick-scan/', views_session.QuickAttendanceScanView.as_view(), name='quick_scan'),

    # API URLs
    path('api/session/create/', views_session.api_create_attendance_session, name='api_session_create'),
    path('api/session/<str:session_id>/validate/', views_session.api_validate_attendance_session, name='api_session_validate'),
]