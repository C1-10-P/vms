# apps/settings/urls.py
from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.SettingsIndexView.as_view(), name='index'),
    path('general/', views.GeneralSettingsView.as_view(), name='general'),
    path('security/', views.SecuritySettingsView.as_view(), name='security'),
    path('notification/', views.NotificationSettingsView.as_view(), name='notification'),
    path('backup/', views.BackupSettingsView.as_view(), name='backup'),
    path('integration/', views.IntegrationSettingsView.as_view(), name='integration'),
    path('audit-logs/', views.AuditLogsView.as_view(), name='audit_logs'),
]