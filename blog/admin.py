from django.contrib import admin
from django.utils.html import format_html
import os

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "published", "published_at", "featured_preview")
    list_filter = ("published", "category")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at",)
    readonly_fields = ("featured_preview",)

    def featured_preview(self, obj):
        if obj.featured_image:
            try:
                path = obj.featured_image.path
                if os.path.exists(path):
                    return format_html(
                        '<img src="{}" style="width:120px;height:auto;border-radius:6px;object-fit:cover;" />',
                        obj.featured_image.url,
                    )
            except Exception:
                # if storage backend doesn't provide path or any error, fall back
                pass
        return "No image"

    featured_preview.short_description = "Featured"
