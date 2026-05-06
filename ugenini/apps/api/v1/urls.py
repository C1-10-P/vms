from rest_framework.routers import DefaultRouter
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.api.v1.attendance_views import AttendanceSessionCreateView, AttendanceSessionValidateView
from apps.vms.views_session import VisitorSessionCreateView, VisitorSessionCompleteView, VisitorTagAssignView

from . import views
from apps.api.v1 import views
from apps.api.v1.ocr_views import OCRProcessIDView, OCRScanAttendanceView, OCRScanVisitorView

router = DefaultRouter()

router.register(r'attendance', views.AttendanceViewSet, basename='attendance')
router.register(r'visitors', views.VisitorViewSet, basename='visitor')
router.register(r'zones', views.ZoneViewSet, basename='zone')
router.register(r'devices', views.DeviceViewSet, basename='device')
router.register(r'users', views.UserViewSet, basename='user')

# router.register(r'reports', views.ReportViewSet, basename='report')

app_name = 'api_v1'

urlpatterns = [

    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),

    # Authentication
    path('auth/login/', views.CustomTokenObtainPairView.as_view()),
    path('auth/refresh/', views.TokenRefreshView.as_view()),
    path('auth/logout/', views.LogoutView.as_view()),
    path('auth/me/', views.CurrentUserView.as_view()),
    path('auth/change-password/', views.ChangePasswordView.as_view()),
    path('auth/reset-password/', views.PasswordResetView.as_view()),
    path('auth/reset-password/confirm/', views.PasswordResetConfirmView.as_view()),

    # Dashboard
    path('dashboard/stats/', views.DashboardStatsView.as_view()),
    path('dashboard/realtime/', views.RealtimeDashboardView.as_view()),
    path('dashboard/alerts/', views.DashboardAlertsView.as_view()),

    # Attendance custom endpoints
    path('attendance/checkin/', views.AttendanceCheckInView.as_view()),
    path('attendance/bulk/', views.BulkAttendanceView.as_view()),
    path('attendance/summary/', views.AttendanceSummaryView.as_view()),
    path('attendance/trends/', views.AttendanceTrendsView.as_view()),
    path('attendance/export/', views.AttendanceExportView.as_view()),

    # Visitors
    path('visitors/checkin/', views.VisitorCheckInView.as_view(), name='visitor_checkin'),
    path('visitors/checkout/<str:tag_uuid>/', views.VisitorCheckOutView.as_view(), name='api_checkout'),
    path('visitors/tracking/', views.VisitorTrackingView.as_view()),
    path('visitors/blacklist/', views.VisitorBlacklistView.as_view()),
    path('visitors/history/', views.VisitorHistoryView.as_view()),

    # Access
    path('access/request/', views.AccessRequestView.as_view()),
    path('access/verify/', views.AccessVerifyView.as_view()),
    path('access/logs/', views.AccessLogView.as_view()),
    path('access/zones/', views.AccessZoneView.as_view()),
    path('access/permissions/', views.AccessPermissionView.as_view()),

    # Devices
    path('devices/heartbeat/', views.DeviceHeartbeatView.as_view()),
    path('devices/register/', views.DeviceRegisterView.as_view()),
    path('devices/command/', views.DeviceCommandView.as_view()),
    path('devices/firmware/', views.FirmwareUpdateView.as_view()),
    path('devices/ota/', views.OTAUpdateView.as_view()),

    # Reports
    path('reports/generate/', views.ReportGenerateView.as_view()),
    path('reports/download/<int:pk>/', views.ReportDownloadView.as_view()),
    path('reports/schedule/', views.ReportScheduleView.as_view()),

    # Notifications
    path('notifications/', views.NotificationView.as_view()),
    path('notifications/mark-read/', views.MarkNotificationReadView.as_view()),
    path('notifications/subscribe/', views.SubscribePushView.as_view()),

    # Search
    path('search/', views.GlobalSearchView.as_view()),
    path('search/students/', views.StudentSearchView.as_view()),
    path('search/visitors/', views.VisitorSearchView.as_view()),
    path('search/devices/', views.DeviceSearchView.as_view()),

    # Stats
    path('stats/attendance/', views.AttendanceStatsView.as_view()),
    path('stats/visitors/', views.VisitorStatsView.as_view()),
    path('stats/devices/', views.DeviceStatsView.as_view()),
    path('stats/access/', views.AccessStatsView.as_view()),

     # Attendance Session Endpoints
    path('attendance/session/create/', AttendanceSessionCreateView.as_view(), name='attendance_session_create'),
    path('attendance/session/<str:session_id>/validate/', AttendanceSessionValidateView.as_view(), name='attendance_session_validate'),
    
    # Visitor Session Endpoints
    path('visitor/session/create/', VisitorSessionCreateView.as_view(), name='visitor_session_create'),
    path('visitor/session/<str:session_id>/complete/', VisitorSessionCompleteView.as_view(), name='visitor_session_complete'),
    path('visitor/session/<str:session_id>/assign-tag/', VisitorTagAssignView.as_view(), name='visitor_tag_assign'),
    
    # OCR Endpoints
    path('ocr/process/', OCRProcessIDView.as_view(), name='ocr_process'),
    path('ocr/attendance/', OCRScanAttendanceView.as_view(), name='ocr_attendance'),
    path('ocr/visitor/', OCRScanVisitorView.as_view(), name='ocr_visitor'),

    path('institutions/<int:pk>/colleges/', views.institution_colleges, name='inst_colleges'),
    path('colleges/<int:pk>/schools/', views.college_schools, name='college_schools'),
    path('schools/<int:pk>/departments/', views.school_departments, name='school_depts'),

    # Router (ONLY ONCE)
    path('', include(router.urls)),
]