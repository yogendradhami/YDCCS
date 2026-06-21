# ====================================================
# YD Commercial Cleaning Services
# File: portal/urls.py
# Purpose:
# - Customer portal routes
# - Authentication
# - Dashboard
# - Bookings
# - Invoices
# - Profile
# - Password reset
# ====================================================

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Customer authentication
    path("portal/register/", views.portal_register, name="portal_register"),
    path("portal/login/", views.portal_login, name="portal_login"),
    path("portal/logout/", views.portal_logout, name="portal_logout"),
    # Customer dashboard
    path("portal/dashboard/", views.portal_dashboard, name="portal_dashboard"),
    # Customer profile
    path("portal/profile/", views.portal_profile, name="portal_profile"),
    # Customer bookings
    path("portal/bookings/", views.portal_bookings, name="portal_bookings"),
    path(
        "portal/bookings/<int:booking_id>/",
        views.booking_detail,
        name="portal_booking_detail",
    ),
    # Customer invoices
    path("portal/invoices/", views.portal_invoices, name="portal_invoices"),
    path(
        "portal/invoices/<int:invoice_id>/",
        views.portal_invoice_detail,
        name="portal_invoice_detail",
    ),
    # Password reset request page
    path(
        "portal/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="portal_password_reset.html",
            email_template_name="portal_password_reset_email.html",
            subject_template_name="portal_password_reset_subject.txt",
            success_url="/portal/password-reset/done/",
        ),
        name="password_reset",
    ),
    # Password reset email sent page
    path(
        "portal/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="portal_password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    # Password reset confirmation page
    path(
        "portal/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="portal_password_reset_confirm.html",
            success_url="/portal/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    # Password reset complete page
    path(
        "portal/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="portal_password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("portal/documents/", views.portal_documents, name="portal_documents"),
]
