"""
URL configuration for AI Application Tester backend.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/admin/', include('apps.users.admin_urls')),
    path('api/applications/', include('apps.applications.urls')),
    path('api/reports/', include('apps.reports.urls')),
]
