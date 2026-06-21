# ====================================================
# YD Commercial Cleaning Services
# File: invoices/admin.py
# Purpose:
# - Manage invoices inside Django Admin
# - Show invoice status badges
# - Show Stripe payment tracking fields
# ====================================================

from django.contrib import admin
from django.utils.html import format_html

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer_name",
        "booking",
        "issue_date",
        "due_date",
        "amount",
        "gst_amount",
        "total_amount",
        "status_badge",
        "paid_at",
        "created_at",
    )

    search_fields = (
        "invoice_number",
        "booking__customer__full_name",
        "booking__customer__phone",
        "booking__customer__email",
        "stripe_checkout_session_id",
        "stripe_payment_intent_id",
    )

    list_filter = (
        "status",
        "issue_date",
        "due_date",
        "paid_at",
        "created_at",
    )

    readonly_fields = (
        "invoice_number",
        "gst_amount",
        "total_amount",
        "stripe_checkout_session_id",
        "stripe_payment_intent_id",
        "paid_at",
        "created_at",
        "updated_at",
    )

    def customer_name(self, obj):
        return obj.booking.customer.full_name

    customer_name.short_description = "Customer"

    def status_badge(self, obj):
        colors = {
            "draft": "#6b7280",
            "sent": "#0d6efd",
            "paid": "#16a34a",
            "overdue": "#dc2626",
            "cancelled": "#111827",
        }

        return format_html(
            (
                '<span style="background:{};color:white;padding:5px 10px;'
                'border-radius:20px;font-weight:bold;">{}</span>'
            ),
            colors.get(obj.status, "#6b7280"),
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
