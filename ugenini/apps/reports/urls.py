# apps/reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = []
    #  Report Dashboard 
#     path('', views.ReportDashboardView.as_view(), name='dashboard'),
#     path('generate/', views.ReportGeneratorView.as_view(), name='generate'),
    
#     #  Attendance Reports 
#     path('attendance/', views.AttendanceReportView.as_view(), name='attendance'),
#     path('attendance/daily/', views.daily_attendance_report, name='daily_attendance'),
#     path('attendance/weekly/', views.weekly_attendance_report, name='weekly_attendance'),
#     path('attendance/monthly/', views.monthly_attendance_report, name='monthly_attendance'),
#     path('attendance/class/<int:class_id>/', views.class_attendance_report, name='class_attendance'),
#     path('attendance/student/<int:student_id>/', views.student_attendance_report, name='student_attendance'),
#     path('attendance/department/<int:department_id>/', views.department_attendance_report, name='department_attendance'),
    
#     #  Visitor Reports 
#     path('visitors/', views.VisitorReportView.as_view(), name='visitors'),
#     path('visitors/daily/', views.daily_visitor_report, name='daily_visitors'),
#     path('visitors/weekly/', views.weekly_visitor_report, name='weekly_visitors'),
#     path('visitors/monthly/', views.monthly_visitor_report, name='monthly_visitors'),
#     path('visitors/summary/', views.visitor_summary_report, name='visitor_summary'),
    
#     #  Access Reports 
#     path('access/', views.AccessReportView.as_view(), name='access'),
#     path('access/summary/', views.access_summary_report, name='access_summary'),
#     path('access/failures/', views.access_failures_report, name='access_failures'),
#     path('access/zone/<int:zone_id>/', views.zone_access_report, name='zone_access'),
    
#     #  Device Reports 
#     path('devices/', views.DeviceReportView.as_view(), name='devices'),
#     path('devices/health/', views.device_health_report, name='device_health'),
#     path('devices/uptime/', views.device_uptime_report, name='device_uptime'),
#     path('devices/performance/', views.device_performance_report, name='device_performance'),
    
#     #  Custom Reports 
#     path('custom/', views.CustomReportView.as_view(), name='custom'),
#     path('custom/create/', views.CustomReportCreateView.as_view(), name='custom_create'),
#     path('custom/<int:pk>/', views.CustomReportDetailView.as_view(), name='custom_detail'),
#     path('custom/<int:pk>/edit/', views.CustomReportUpdateView.as_view(), name='custom_edit'),
#     path('custom/<int:pk>/delete/', views.CustomReportDeleteView.as_view(), name='custom_delete'),
    
#     #  Scheduled Reports 
#     path('schedules/', views.ReportScheduleListView.as_view(), name='schedule_list'),
#     path('schedules/create/', views.ReportScheduleCreateView.as_view(), name='schedule_create'),
#     path('schedules/<int:pk>/', views.ReportScheduleDetailView.as_view(), name='schedule_detail'),
#     path('schedules/<int:pk>/edit/', views.ReportScheduleUpdateView.as_view(), name='schedule_edit'),
#     path('schedules/<int:pk>/delete/', views.ReportScheduleDeleteView.as_view(), name='schedule_delete'),
#     path('schedules/<int:pk>/run/', views.run_scheduled_report, name='run_schedule'),
    
#     #  Report Exports 
#     path('export/<int:pk>/pdf/', views.export_report_pdf, name='export_pdf'),
#     path('export/<int:pk>/excel/', views.export_report_excel, name='export_excel'),
#     path('export/<int:pk>/csv/', views.export_report_csv, name='export_csv'),
#     path('export/<int:pk>/json/', views.export_report_json, name='export_json'),
    
#     #  Report History 
#     path('history/', views.ReportHistoryView.as_view(), name='history'),
#     path('history/<int:pk>/', views.ReportHistoryDetailView.as_view(), name='history_detail'),
#     path('history/<int:pk>/download/', views.download_report, name='download_report'),
#     path('history/<int:pk>/delete/', views.delete_report, name='delete_report'),
    
#     #  API Endpoints 
#     path('api/generate/', views.api_generate_report, name='api_generate'),
#     path('api/status/<str:task_id>/', views.api_report_status, name='api_status'),
#     path('api/schedules/', views.api_schedule_list, name='api_schedule_list'),
    
#     #  AJAX Endpoints 
#     path('ajax/report-preview/', views.ajax_report_preview, name='ajax_preview'),
#     path('ajax/available-fields/', views.ajax_available_fields, name='ajax_fields'),
#     path('ajax/report-progress/<str:task_id>/', views.ajax_report_progress, name='ajax_progress'),
# ]