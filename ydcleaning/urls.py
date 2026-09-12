# ====================================================
# YD Commercial Cleaning Services
# File: ydcleaning/urls.py
# Purpose:
# - Main project URL configuration
# ====================================================

from django.contrib import admin
from django.urls import include, path
from core.health import health_check

urlpatterns = [
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("analytics/", include(("analytics.urls", "analytics"), namespace="analytics")),
    path("", include("dashboard.urls")),
    # Corporate
    path(
        "corporate/",
        include("corporate.urls"),
    ),


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