from django.contrib import admin
from django.utils.html import format_html
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "is_active",
        "hero_preview"
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "description",
        "overview"
    )

    prepopulated_fields = {
        "slug": ("name",)
    }


    fieldsets = (

        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "overview",
                    "introduction",
                    "hero_image",
                    "hero_preview",
                    "is_active",
                )
            }
        ),


        (
            "SEO Content Sections",
            {
                "fields": (
                    "ideal_for",
                    "industries",
                    "process",
                    "problems",
                    "faqs",
                )
            }
        ),


        (
            "Service Details",
            {
                "fields": (
                    "included",
                    "packages",
                )
            }
        ),

    )


    readonly_fields = (
        "hero_preview",
    )


    def hero_preview(self, obj):

        if obj.hero_image:

            return format_html(
                '<img src="{}" width="120" height="80" style="object-fit:cover;border-radius:8px;">',
                obj.hero_image.url
            )

        return "No Image"


    hero_preview.short_description = "Preview"