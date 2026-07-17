# ====================================================
# YD Commercial Cleaning Services
# File: config/urls.py
# Purpose:
# - Main project URL configuration for the reorganized `config/` entrypoint.
# ====================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('dashboard.urls')),
    path('', include('payroll.urls')),
    path('', include('invoices.urls')),
    path('', include('portal.urls')),
    path('', include('employees.urls')),
    path('', include('reports.urls')),
    path('', include('gallery.urls')),
    path('', include('reviews.urls')),
    path('', include('notifications.urls')),
    path('', include('contracts.urls')),
    path('', include('attendance.urls')),
    path('', include('leave_management.urls')),
    path('', include('rosters.urls')),
    path('', include('payroll.urls')),
    path('', include('expenses.urls')),
    path('', include('google_reviews.urls')),
    path('', include('support.urls')),

    path('', include('core.urls')),
]

handler404 = 'core.views.custom_page_not_found'

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
