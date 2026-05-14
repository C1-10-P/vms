"""
URL configuration for ugenini project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from apps.dashboard.views import home

# API Documentation
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from drf_spectacular.views import SpectacularAPIView

# Schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Ugenini",
        default_version='v1',
        description=
        """
        
        ## Authentication
        Use JWT token obtained from `/api/v1/auth/login/`
        
        """,
        # terms_of_service="https://www.jkuat.ac.ke/terms/",
        # contact=openapi.Contact(email="vms@jkuat.ac.ke"),
        # license=openapi.License(name="JKUAT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    

    # Authentication & User Apps
    path('verify/', include('apps.verify.urls')), 
    path('dashboard/', include('apps.dashboard.urls')),
    path('settings/', include('apps.settings.urls')),
    
    # Modules
    path('core/', include('apps.core.urls')),
    path('classroom/', include('apps.classroom.urls')),
    path('access/', include('apps.access.urls')),
    # path('kizaru/', include('apps.kizaru.routing')),
    path('vms/', include('apps.vms.urls')),
    path('devices/', include('apps.firmware.urls')),
    path('users/', include('apps.users.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('ocr/', include('apps.ocr.urls')),
    

    # API & Docs
    path('api/v1/', include('apps.api.v1.urls')), 
    path('api/v1/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    re_path(r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json"
    ),
    path("swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui"
    ),

    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),

    # Redirect root to login
    # path('', lambda request: redirect('verify:login'), name='root_redirect'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

# Custom error handlers
# handler404 = 'apps.core.views.handler404'
# handler500 = 'apps.core.views.handler500'
# handler403 = 'apps.core.views.handler403'
