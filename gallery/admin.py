# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

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

    def _build_gallery_media_html(self, obj, thumb_size=60, max_items=None):
        media = list(obj.gallery_media)
        if not media:
            return "No image"

        if max_items is None:
            max_items = len(media)

        html_parts = [
            '<div style="display:flex; gap:8px; flex-wrap:wrap; align-items:flex-start;">'
        ]

        for item in media[:max_items]:
            if item["is_image"]:
                html_parts.append(
                    format_html(
                        '<div><img src="{}" width="{}" height="{}" '
                        'style="object-fit:cover;border-radius:6px;" /></div>',
                        item["url"],
                        thumb_size,
                        thumb_size,
                    )
                )
            else:
                html_parts.append(
                    format_html(
                        '<div style="min-width:150px; padding:12px; border:1px solid #ddd; border-radius:6px;">'
                        '<strong>{}</strong><br><a href="{}" target="_blank">Open file</a></div>',
                        item["name"],
                        item["url"],
                    )
                )

        if len(media) > max_items:
            html_parts.append(
                '<span style="align-self:center; color:#666; font-size:12px;">+ more</span>'
            )

        html_parts.append('</div>')
        return mark_safe(''.join(html_parts))

    def image_preview(self, obj):
        return self._build_gallery_media_html(obj, thumb_size=60, max_items=3)
    image_preview.short_description = "Preview"

    def gallery_preview(self, obj):
        """Full preview of all media in a single grouped card"""
        return self._build_gallery_media_html(obj, thumb_size=150, max_items=None)
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

