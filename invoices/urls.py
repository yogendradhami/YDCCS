# ====================================================
# YD Commercial Cleaning Services
# File: invoices/urls.py
# Purpose:
# - Invoice URL routing
# - Stripe payment URL routing
# ====================================================

from django.urls import path

from .views import (
    create_invoice,
    create_stripe_checkout_session,
    download_invoice_pdf,
    invoice_detail,
    invoice_list,
    stripe_payment_cancel,
    stripe_payment_success,
)

urlpatterns = [
    path("dashboard/invoices/", invoice_list, name="invoice_list"),
    path("dashboard/invoices/create/", create_invoice, name="create_invoice"),
    path("dashboard/invoices/<int:invoice_id>/", invoice_detail, name="invoice_detail"),
    path(
        "dashboard/invoices/<int:invoice_id>/download/",
        download_invoice_pdf,
        name="download_invoice_pdf",
    ),
    path(
        "dashboard/invoices/<int:invoice_id>/pay/",
        create_stripe_checkout_session,
        name="create_stripe_checkout_session",
    ),
    path(
        "dashboard/invoices/<int:invoice_id>/payment-success/",
        stripe_payment_success,
        name="stripe_payment_success",
    ),
    path(
        "dashboard/invoices/<int:invoice_id>/payment-cancel/",
        stripe_payment_cancel,
        name="stripe_payment_cancel",
    ),
]
