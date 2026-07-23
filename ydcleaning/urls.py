# ====================================================
# YD Commercial Cleaning Services
# File: ydcleaning/urls.py
# Purpose:
# - Main project URL configuration
# ====================================================

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("", include("payroll.urls")),
    path("", include("invoices.urls")),
    path("", include("portal.urls")),
    path("", include("employees.urls")),
    path("", include("reports.urls")),
    path("", include("gallery.urls")),
    path("", include("reviews.urls")),
    path("", include("notifications.urls")),
    path("", include("contracts.urls")),
    path("", include("attendance.urls")),
    path("", include("leave_management.urls")),
    path("", include("rosters.urls")),
    path("", include("expenses.urls")),
    path("", include("google_reviews.urls")),
    path("", include("support.urls")),
    path("", include("core.urls")),
]

# Serve uploaded media files from MEDIA_ROOT. This is required when the deployment container
# does not have an external media host configured.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
