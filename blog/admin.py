from django.contrib import admin
from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.html import format_html
import os

from .models import BlogPost


class BlogPostAdminForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = "__all__"

    def clean_featured_image(self):
        image = self.cleaned_data.get("featured_image")
        if isinstance(image, UploadedFile) and image.size > 15 * 1024 * 1024:
            raise forms.ValidationError("Blog images must be 15 MB or smaller.")
        return image


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    form = BlogPostAdminForm
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
