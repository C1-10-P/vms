from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    #  Notification Management 
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    path('<int:pk>/mark-read/', views.NotificationMarkReadView.as_view(), name='mark_read'),
    
    # path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    # path('delete-all-read/', views.delete_all_read, name='delete_all_read'),
    
    #  Notification Settings 
    # path('settings/', views.NotificationSettingsView.as_view(), name='settings'),
    # path('settings/update/', views.update_notification_settings, name='update_settings'),
    
    #  SMS Logs 
    path('sms/', views.SMSLogListView.as_view(), name='sms_logs'),
    # path('sms/<int:pk>/', views.SMSLogDetailView.as_view(), name='sms_detail'),
    # path('sms/resend/<int:pk>/', views.resend_sms, name='resend_sms'),
    
    #  Email Logs 
    path('emails/', views.EmailLogListView.as_view(), name='email_logs'),
    # path('emails/<int:pk>/', views.EmailLogDetailView.as_view(), name='email_detail'),
    # path('emails/resend/<int:pk>/', views.resend_email, name='resend_email'),
    
    #  USSD Callback 
    path('ussd-callback/', views.ussd_callback, name='ussd_callback'),
    # path('ussd-sessions/', views.USSDSessionListView.as_view(), name='ussd_sessions'),
    # path('ussd-sessions/<int:pk>/', views.USSDSessionDetailView.as_view(), name='ussd_detail'),
    
    #  Push Notifications 
    # path('push/register/', views.register_push_device, name='register_push'),
    # path('push/unregister/', views.unregister_push_device, name='unregister_push'),
    # path('push/test/', views.test_push_notification, name='test_push'),
    
    # #  API Endpoints 
    # path('api/send/', views.api_send_notification, name='api_send'),
    # path('api/broadcast/', views.api_broadcast_notification, name='api_broadcast'),
    # path('api/stats/', views.api_notification_stats, name='api_stats'),
    
    # #  AJAX Endpoints 
    # path('ajax/unread-count/', views.ajax_unread_count, name='ajax_unread_count'),
    # path('ajax/recent/', views.ajax_recent_notifications, name='ajax_recent'),
    # path('ajax/mark-read/<int:pk>/', views.ajax_mark_read, name='ajax_mark_read'),
]