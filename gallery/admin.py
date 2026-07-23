# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryItem


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "service_type",
        "suburb",
        "featured",
        "before_preview",
        "after_preview",
        "created_at",
    )

    list_filter = (
        "service_type",
        "featured",
        "created_at",
    )

    search_fields = (
        "title",
        "service_type",
        "suburb",
    )

    def before_preview(self, obj):
        if obj.before_image:
            return format_html(
                (
                    '<img src="{}" width="80" height="60" '
                    'style="object-fit:cover;border-radius:6px;" />'
                ),
                obj.before_image.url,
            )
        return "No image"

    def after_preview(self, obj):
        if obj.after_image:
            return format_html(
                (
                    '<img src="{}" width="80" height="60" '
                    'style="object-fit:cover;border-radius:6px;" />'
                ),
                obj.after_image.url,
            )
        return "No image"

    before_preview.short_description = "Before"
    after_preview.short_description = "After"
