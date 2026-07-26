from django.contrib import admin
from django.utils.html import format_html
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
            return format_html(
                '<img src="{}" style="width:120px;height:80px;border-radius:6px;object-fit:cover;" />',
                obj.hero_image.url,
            )

        return "No image"

    hero_preview.short_description = "Hero"