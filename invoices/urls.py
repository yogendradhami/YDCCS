# ====================================================
# YD Commercial Cleaning Services
# File: invoices/urls.py
# Purpose:
# - Invoice URL routing
# - Stripe payment URL routing
# ====================================================

from django.urls import path

from .views import (
    cancel_invoice,
    create_invoice,
    create_stripe_checkout_session,
    delete_invoice,
    download_invoice_pdf,
    edit_invoice,
    invoice_detail,
    invoice_list,
    mark_invoice_paid,
    mark_invoice_unpaid,
    stripe_payment_cancel,
    stripe_payment_cancel_return,
    stripe_payment_return,
    stripe_payment_success,
    stripe_pay_invoice_link,
    stripe_webhook,
)

urlpatterns = [
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path(
        "invoice/pay/<str:token>/",
        stripe_pay_invoice_link,
        name="invoice_stripe_pay_link",
    ),
    path(
        "invoice/payment-return/<str:token>/",
        stripe_payment_return,
        name="stripe_payment_return",
    ),
    path(
        "invoice/payment-cancelled/<str:token>/",
        stripe_payment_cancel_return,
        name="stripe_payment_cancel_return",
    ),
    path("dashboard/invoices/", invoice_list, name="invoice_list"),
    path("dashboard/invoices/create/", create_invoice, name="create_invoice"),

    path(
        "dashboard/invoices/<int:invoice_id>/edit/",
        edit_invoice,
        name="edit_invoice",
    ),

    path(
        "dashboard/invoices/<int:invoice_id>/mark-paid/",
        mark_invoice_paid,
        name="mark_invoice_paid",
    ),
    path(
        "dashboard/invoices/<int:invoice_id>/mark-unpaid/",
        mark_invoice_unpaid,
        name="mark_invoice_unpaid",
    ),

    path(
        "dashboard/invoices/<int:invoice_id>/cancel/",
        cancel_invoice,
        name="cancel_invoice",
    ),

    path(
        "dashboard/invoices/<int:invoice_id>/delete/",
        delete_invoice,
        name="delete_invoice",
    ),
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
    path(
        "portal/invoices/<int:invoice_id>/pay/",
        create_stripe_checkout_session,
        name="portal_create_stripe_checkout_session",
    ),
    path(
        "portal/invoices/<int:invoice_id>/payment-success/",
        stripe_payment_success,
        name="portal_stripe_payment_success",
    ),
    path(
        "portal/invoices/<int:invoice_id>/payment-cancel/",
        stripe_payment_cancel,
        name="portal_stripe_payment_cancel",
    ),
    path(
        "portal/invoices/<int:invoice_id>/download/",
        download_invoice_pdf,
        name="portal_download_invoice_pdf",
    ),
]
