from django.urls import path

from apps.vms import views_session, views_map
from . import views

app_name = 'vms'

urlpatterns = [
    #  Main Views 
    path('', views.VisitorListView.as_view(), name='list'),
    path('checkin/', views.VisitorCheckInView.as_view(), name='checkin'),
    path('checkout/<int:pk>/', views.VisitorCheckOutView.as_view(), name='checkout'),
    path('<int:pk>/', views.VisitorDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.VisitorUpdateView.as_view(), name='edit'),
    # path('<int:pk>/blacklist/', views.VisitorBlacklistView.as_view(), name='blacklist'),
    
    #  Tracking 
    path('tracking/', views.VisitorTrackingView.as_view(), name='tracking'),
    path('tracking-map/', views.visitor_tracking_map, name='tracking_map'),
    path('visitors/<int:pk>/movements/', views.visitor_movement_history, name='visitor_movements'),
    path('live-tracking/', views.visitor_live_tracking, name='live_tracking'),
    path('api/tracking/refresh/', views.refresh_tracking_data, name='refresh_tracking'),
    
    #  Tag Management 
    path('tags/', views.BLETagListView.as_view(), name='tag_list'),
    path('tags/create/', views.BLETagCreateView.as_view(), name='tag_create'),
    path('tags/<int:pk>/', views.BLETagDetailView.as_view(), name='tag_detail'),
    path('tags/<int:pk>/edit/', views.get_tag_edit_form, name='tag_edit'),
    path('tags/<int:pk>/update/', views.update_tag, name='tag_update'),
    path('tags/<int:pk>/assign/', views.BLETagAssignView.as_view(), name='tag_assign'),
    path('tags/<int:pk>/release/', views.BLETagReleaseView.as_view(), name='tag_release'),
    path('tags/<int:pk>/maintenance/', views.BLETagMaintenanceView.as_view(), name='tag_maintenance'),
    # path('tags/<int:pk>/toggle-status/', views.toggle_tag_status, name='tag_toggle_status'),
    
    #  Reports 
    path('reports/', views.VisitorReportView.as_view(), name='report'),
    path('reports/daily/', views.daily_visitor_report, name='daily_report'),
    path('reports/weekly/', views.weekly_visitor_report, name='weekly_report'),
    path('reports/monthly/', views.monthly_visitor_report, name='monthly_report'),
    
    #  Exports 
    # path('export/csv/', views.export_visitors_csv, name='export_csv'),
    path('export/excel/', views.export_visitors_excel, name='export_excel'),
    
    #  API Endpoints 
    path('api/checkin/', views.api_visitor_checkin, name='api_checkin'),
    path('api/checkout/<str:tag_uuid>/', views.api_visitor_checkout, name='api_checkout'),
    # path('api/tracking/<str:tag_uuid>/', views.api_visitor_tracking, name='api_tracking'),
    path('api/location/', views.api_update_location, name='api_location'),
    
    #  AJAX Endpoints 
    path('ajax/search/', views.ajax_search_visitors, name='ajax_search'),
    path('ajax/active-count/', views.ajax_active_visitors_count, name='ajax_active_count'),
    path('ajax/tag-status/<str:tag_uuid>/', views.ajax_tag_status, name='ajax_tag_status'),
    
    #  Alerts 
    path('alerts/', views.VisitorAlertListView.as_view(), name='alert_list'),
    path('alerts/<int:pk>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('alerts/<int:pk>/resolve/', views.resolve_alert, name='resolve_alert'),

     # Session URLs
    path('sessions/', views_session.VisitorSessionListView.as_view(), name='session_list'),
    path('sessions/create/', views_session.VisitorSessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/', views_session.VisitorSessionDetailView.as_view(), name='session_detail'),
    path('sessions/checkin/<str:session_id>/', views_session.VisitorCheckinSessionView.as_view(), name='session_checkin'),
    path('sessions/complete/<str:session_id>/', views_session.VisitorSessionCompleteView.as_view(), name='session_complete'),
    path('sessions/tag/<str:session_id>/', views_session.VisitorTagAssignView.as_view(), name='session_tag_assign'),
    path('sessions/<int:pk>/detail-json/', views_session.get_session_detail_json, name='session_detail_json'),
    path('ocr-process/', views_session.VisitorOCRProcessView.as_view(), name='ocr_process'),
    path('sessions/create-checkin/', views_session.create_checkin_session, name='create_checkin_session'),
    path('sessions/<str:session_id>/get-data/', views_session.get_session_data, name='get_session_data'),
    path('sessions/process-ocr/', views_session.process_ocr_image, name='process_ocr'),
    path('sessions/complete-checkin/', views_session.complete_checkin_session, name='complete_checkin'),
    path('sessions/<str:session_id>/assign-tag/', views_session.assign_tag_to_session, name='assign_tag'),
    
    # API URLs
    path('api/session/create/', views_session.api_create_visitor_session, name='api_session_create'),
    path('api/session/<str:session_id>/complete/', views_session.api_complete_visitor_session, name='api_session_complete'),
    path('api/session/<str:session_id>/assign-tag/', views_session.api_assign_tag_to_session, name='api_assign_tag'),
    path('api/session/<str:session_id>/status/', views_session.api_get_session_status, name='api_session_status'),

    # Map Views
    path('map/', views_map.VisitorMapView.as_view(), name='visitor_map'),
    path('api/movement/', views_map.VisitorMovementAPIView.as_view(), name='api_movement'),
    path('api/heatmap/', views_map.VisitorHeatmapView.as_view(), name='api_heatmap'),
    # path('api/movement/data/', views.VisitorMovementDataView.as_view(), name='visitor_movement_data'),
    path('timeline/<int:visitor_id>/', views_map.VisitorTimelineView.as_view(), name='visitor_timeline'),
]