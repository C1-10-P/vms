from django.urls import path
from . import views
from apps.core.services import DashboardService

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardHomeView.as_view(), name='home'),
    path('chart-data/', DashboardService.get_chart_data, name='chart_data'),
]

