from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, JobPhoto


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "service_type",
        "booking_date",
        "booking_time",
        "suburb_postcode",
        "quoted_price",
        "assigned_employee",
        "status_badge",
        "report_link",
    )

    search_fields = (
        "customer__full_name",
        "service_type",
        "suburb_postcode",
        "assigned_employee__full_name",
    )

    list_filter = (
        "status",
        "service_type",
        "booking_date",
        "assigned_employee",
    )

    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "confirmed": "#0d6efd",
            "assigned": "#9333ea",
            "in_progress": "#16a34a",
            "completed": "#15803d",
            "cancelled": "#dc2626",
        }

        return format_html(
<<<<<<< HEAD
            (
                '<span style="background:{};color:white;padding:5px 10px;'
                'border-radius:20px;font-weight:bold;">{}</span>'
            ),
            colors.get(obj.status, "#6b7280"),
            obj.get_status_display(),
=======
            '<span style="background:{};color:white;padding:5px 10px;border-radius:20px;font-weight:bold;">{}</span>',
            colors.get(obj.status, "#6b7280"),
            obj.get_status_display()
>>>>>>> 5815f15 (Initial project commit)
        )

    status_badge.short_description = "Status"

    def report_link(self, obj):
        return format_html(
            '<a href="/reports/booking/{}/" target="_blank">View Report</a> | '
            '<a href="/reports/booking/{}/download/" target="_blank">PDF</a>',
            obj.id,
<<<<<<< HEAD
            obj.id,
=======
            obj.id
>>>>>>> 5815f15 (Initial project commit)
        )

    report_link.short_description = "Report"


@admin.register(JobPhoto)
class JobPhotoAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "employee",
        "photo_type",
        "image_preview",
        "uploaded_at",
    )

    list_filter = (
        "photo_type",
        "uploaded_at",
    )

    search_fields = (
        "booking__customer__full_name",
        "employee__full_name",
        "notes",
    )

    readonly_fields = (
        "image_preview",
        "uploaded_at",
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:120px;height:auto;border-radius:8px;" />',
<<<<<<< HEAD
                obj.image.url,
=======
                obj.image.url
>>>>>>> 5815f15 (Initial project commit)
            )

        return "No image"

<<<<<<< HEAD
    image_preview.short_description = "Preview"
=======
    image_preview.short_description = "Preview"
>>>>>>> 5815f15 (Initial project commit)
