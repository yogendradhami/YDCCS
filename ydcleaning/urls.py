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
    # ====================================================
    # SYSTEM / ADMIN
    # ====================================================

    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),

    # ====================================================
    # ANALYTICS
    # ====================================================

    path(
        "analytics/",
        include(
            ("analytics.urls", "analytics"),
            namespace="analytics",
        ),
    ),

    # ====================================================
    # DASHBOARD
    # ====================================================

    path("", include("dashboard.urls")),

    # ====================================================
    # CORPORATE
    # ====================================================

    path(
        "corporate/",
        include("corporate.urls"),
    ),

    # ====================================================
    # BUSINESS / OPERATIONS
    # ====================================================

    path("", include("payroll.urls")),
    path("", include("invoices.urls")),
    path("", include("portal.urls")),
    path("", include("employees.urls")),
    path("", include("induction.urls")),
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

    # ====================================================
    # CUSTOMER CLEANING CHALLENGE
    #
    # IMPORTANT:
    # This MUST appear before core.urls.
    #
    # core.urls contains:
    #     <slug:service_slug>/
    #
    # which otherwise catches:
    #     /cleaning-challenge/
    # and redirects it to:
    #     /services/cleaning-challenge/
    # ====================================================

    path(
        "cleaning-challenge/",
        include("cleaning_game.urls"),
    ),

    # ====================================================
    # MAIN WEBSITE
    #
    # Keep core.urls AFTER cleaning-challenge because
    # core.urls contains the generic legacy service route.
    # ====================================================

    path(
        "",
        include("core.urls"),
    ),

    # ====================================================
    # COMPANY DOCUMENTS
    # ====================================================

    path(
        "dashboard/company-documents/",
        include("company_documents.urls"),
    ),
]