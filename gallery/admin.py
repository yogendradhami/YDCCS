# gallery/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .forms import GalleryItemForm, GalleryMediaForm
from .models import GalleryItem, GalleryMedia


class GalleryMediaInline(admin.TabularInline):
    """
    Allows multiple additional images to be uploaded
    inside one GalleryItem.
    """

    model = GalleryMedia
    form = GalleryMediaForm

    extra = 3

    fields = (
        "media_type",
        "image",
        "image_preview",
        "order",
    )

    readonly_fields = (
        "image_preview",
    )

    ordering = (
        "order",
        "created_at",
    )

    verbose_name = "Additional Gallery Image"
    verbose_name_plural = "Additional Gallery Images"

    def image_preview(self, obj):
        if not obj or not obj.image:
            return "No image"

        try:
            return format_html(
                '<img src="{}" width="120" height="90" '
                'style="object-fit:cover;border-radius:8px;'
                'border:1px solid #ddd;" />',
                obj.image.url,
            )
        except Exception:
            return "Unable to preview"

    image_preview.short_description = "Preview"


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):

    form = GalleryItemForm

    inlines = [
        GalleryMediaInline,
    ]

    list_display = (
        "title",
        "service_type",
        "source",
        "suburb",
        "featured",
        "image_preview",
        "additional_image_count",
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
        "additional_images_preview",
    )

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "title",
                    "service_type",
                    "suburb",
                    "source",
                )
            },
        ),
        (
            "Main Images",
            {
                "fields": (
                    "before_image",
                    "after_image",
                    "image",
                    "gallery_preview",
                )
            },
        ),
        (
            "Gallery Information",
            {
                "fields": (
                    "description",
                    "featured",
                    "job_photo",
                    "job_photo_link",
                    "additional_images_preview",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    def _build_gallery_media_html(
        self,
        obj,
        thumb_size=60,
        max_items=None,
    ):
        media = list(obj.gallery_media)

        if not media:
            return "No image"

        if max_items is None:
            max_items = len(media)

        html_parts = [
            '<div style="display:flex;gap:8px;'
            'flex-wrap:wrap;align-items:flex-start;">'
        ]

        for item in media[:max_items]:

            if item["is_image"]:

                html_parts.append(
                    format_html(
                        '<div>'
                        '<img src="{}" width="{}" height="{}" '
                        'style="object-fit:cover;'
                        'border-radius:6px;'
                        'border:1px solid #ddd;" />'
                        "</div>",
                        item["url"],
                        thumb_size,
                        thumb_size,
                    )
                )

            else:

                html_parts.append(
                    format_html(
                        '<div style="min-width:150px;'
                        'padding:12px;border:1px solid #ddd;'
                        'border-radius:6px;">'
                        "<strong>{}</strong><br>"
                        '<a href="{}" target="_blank">'
                        "Open file"
                        "</a>"
                        "</div>",
                        item["name"],
                        item["url"],
                    )
                )

        if len(media) > max_items:

            html_parts.append(
                '<span style="align-self:center;'
                'color:#666;font-size:12px;">'
                "+ more"
                "</span>"
            )

        html_parts.append("</div>")

        return mark_safe(
            "".join(html_parts)
        )

    def image_preview(self, obj):
        return self._build_gallery_media_html(
            obj,
            thumb_size=60,
            max_items=4,
        )

    image_preview.short_description = "Preview"

    def gallery_preview(self, obj):
        return self._build_gallery_media_html(
            obj,
            thumb_size=150,
            max_items=None,
        )

    gallery_preview.short_description = "Gallery Preview"

    def additional_image_count(self, obj):
        count = obj.media_files.filter(
            media_type="image"
        ).count()

        return count

    additional_image_count.short_description = "Extra Images"

    def additional_images_preview(self, obj):
        media = obj.media_files.filter(
            media_type="image"
        ).order_by(
            "order",
            "created_at",
        )

        if not media.exists():
            return "No additional gallery images yet."

        html = [
            '<div style="display:flex;'
            'gap:10px;flex-wrap:wrap;">'
        ]

        for item in media:

            if not item.image:
                continue

            try:
                html.append(
                    format_html(
                        '<div style="width:150px;">'
                        '<img src="{}" width="150" height="110" '
                        'style="object-fit:cover;'
                        'border-radius:8px;'
                        'border:1px solid #ddd;" />'
                        '<div style="font-size:12px;'
                        'margin-top:4px;color:#666;">'
                        "Order: {}"
                        "</div>"
                        "</div>",
                        item.image.url,
                        item.order,
                    )
                )
            except Exception:
                continue

        html.append("</div>")

        return mark_safe(
            "".join(html)
        )

    additional_images_preview.short_description = (
        "Current Additional Gallery Images"
    )

    def job_photo_link(self, obj):
        if obj.job_photo:

            url = (
                f"/admin/bookings/jobphoto/"
                f"{obj.job_photo.id}/change/"
            )

            return format_html(
                '<a href="{}" target="_blank">'
                "View Job Photo →"
                "</a>",
                url,
            )

        return "Not linked to job photo"

    job_photo_link.short_description = "Linked Job Photo"

    def delete_action(self, obj):
        return format_html(
            '<a class="button" '
            'style="background-color:#d4534f;" '
            'href="/admin/gallery/galleryitem/{}/delete/">'
            "Delete"
            "</a>",
            obj.pk,
        )

    delete_action.short_description = "Action"

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):
        readonly = list(
            self.readonly_fields
        )

        if obj and obj.job_photo:
            readonly.append("source")

        return readonly


@admin.register(GalleryMedia)
class GalleryMediaAdmin(admin.ModelAdmin):

    form = GalleryMediaForm

    list_display = (
        "gallery",
        "media_type",
        "image_preview",
        "order",
        "created_at",
    )

    list_filter = (
        "media_type",
        "video_platform",
    )

    search_fields = (
        "gallery__title",
    )

    ordering = (
        "gallery",
        "order",
        "created_at",
    )

    readonly_fields = (
        "image_preview",
        "created_at",
    )

    fieldsets = (
        (
            "Gallery",
            {
                "fields": (
                    "gallery",
                )
            },
        ),
        (
            "Media",
            {
                "fields": (
                    "media_type",
                    "image",
                    "image_preview",
                    "video_platform",
                    "video_url",
                    "video_thumbnail",
                    "order",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )

    def image_preview(self, obj):

        if not obj or not obj.image:
            return "No image"

        try:
            return format_html(
                '<img src="{}" width="150" height="110" '
                'style="object-fit:cover;'
                'border-radius:8px;'
                'border:1px solid #ddd;" />',
                obj.image.url,
            )
        except Exception:
            return "Unable to preview"

    image_preview.short_description = "Preview"