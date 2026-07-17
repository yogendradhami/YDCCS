# ====================================================
# YD Commercial Cleaning Services
# File: quotes/admin.py
# Purpose: Manage quote requests inside Django Admin
# ====================================================

from django.contrib import admin
from django.utils.html import format_html

<<<<<<< HEAD
from .models import QuoteImage, QuoteRequest
=======
from .models import QuoteRequest, QuoteImage
>>>>>>> 5815f15 (Initial project commit)


class QuoteImageInline(admin.TabularInline):
    model = QuoteImage
    extra = 0
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
<<<<<<< HEAD
                '<a href="{}" target="_blank">View Image</a>', obj.image.url
=======
                '<a href="{}" target="_blank">View Image</a>',
                obj.image.url
>>>>>>> 5815f15 (Initial project commit)
            )
        return "No image"

    image_preview.short_description = "Uploaded Image"


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone",
        "property_type",
        "suburb_postcode",
        "preferred_date",
        "status_badge",
        "created_at",
        "lead_source",
    )

    search_fields = (
        "name",
        "email",
        "phone",
        "suburb_postcode",
    )

    list_filter = (
        "status",
        "property_type",
        "preferred_date",
        "created_at",
    )

    readonly_fields = ("created_at",)

    inlines = [QuoteImageInline]

    def status_badge(self, obj):
        colors = {
            "new": "#0d6efd",
            "contacted": "#f59e0b",
            "quoted": "#9333ea",
            "booked": "#16a34a",
            "completed": "#15803d",
            "lost": "#dc2626",
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


@admin.register(QuoteImage)
class QuoteImageAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    list_display = ("quote", "image", "uploaded_at")
=======
    list_display = ("quote", "image", "uploaded_at")
>>>>>>> 5815f15 (Initial project commit)
