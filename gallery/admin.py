# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryItem


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "service_type",
        "source",
        "suburb",
        "featured",
        "image_preview",
        "created_at",
        "delete_action",
    )

    list_filter = (
        "service_type",
        "source",
        "featured",
        "created_at",
    )

    search_fields = (
        "title",
        "service_type",
        "suburb",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "gallery_preview",
        "job_photo_link",
    )

    fieldsets = (
        ("Basic Info", {
            "fields": ("title", "service_type", "suburb", "source")
        }),
        ("Images", {
            "fields": ("before_image", "after_image", "image", "gallery_preview")
        }),
        ("Details", {
            "fields": ("description", "featured", "job_photo", "job_photo_link")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def image_preview(self, obj):
        if obj.primary_image:
            return format_html(
                '<img src="{}" width="60" height="60" '
                'style="object-fit:cover;border-radius:6px;" />',
                obj.primary_image.url,
            )
        return "No image"
    image_preview.short_description = "Preview"

    def gallery_preview(self, obj):
        """Full preview of all images"""
        html = '<div style="display: flex; gap: 15px; flex-wrap: wrap;">'
        
        if obj.before_image:
            html += format_html(
                '<div><strong>Before:</strong><br><img src="{}" width="150" height="120" style="object-fit:cover;border-radius:6px;"/></div>',
                obj.before_image.url,
            )
        
        if obj.after_image:
            html += format_html(
                '<div><strong>After:</strong><br><img src="{}" width="150" height="120" style="object-fit:cover;border-radius:6px;"/></div>',
                obj.after_image.url,
            )
        
        if obj.image and (not obj.before_image and not obj.after_image):
            html += format_html(
                '<div><strong>Image:</strong><br><img src="{}" width="150" height="120" style="object-fit:cover;border-radius:6px;"/></div>',
                obj.image.url,
            )
        
        html += '</div>'
        return format_html(html)
    gallery_preview.short_description = "Gallery Preview"

    def job_photo_link(self, obj):
        """Link to associated job photo"""
        if obj.job_photo:
            url = f"/admin/bookings/jobphoto/{obj.job_photo.id}/change/"
            return format_html('<a href="{}" target="_blank">View Job Photo →</a>', url)
        return "Not linked to job photo"
    job_photo_link.short_description = "Linked Job Photo"

    def delete_action(self, obj):
        """Quick delete button"""
        return format_html(
            '<a class="button" style="background-color: #d4534f;" href="/admin/gallery/galleryitem/{}/delete/">Delete</a>',
            obj.pk
        )
    delete_action.short_description = "Action"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.job_photo:
            # Make source field readonly if linked to job photo
            readonly.append("source")
        return readonly

