from django.contrib import admin
from django.utils.html import format_html
import os

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "hero_preview")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "overview")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("hero_preview",)

    def hero_preview(self, obj):
        if obj.hero_image:
            try:
                path = obj.hero_image.path
                if os.path.exists(path):
                    return format_html(
                        '<img src="{}" style="width:120px;height:auto;border-radius:6px;object-fit:cover;" />',
                        obj.hero_image.url,
                    )
            except Exception:
                pass

        return "No image"

    hero_preview.short_description = "Hero"
