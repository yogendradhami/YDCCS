# ============================================================
# YD Commercial Cleaning Services
# File: gallery/admin.py
# ============================================================

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .forms import GalleryItemForm
from .models import GalleryImage
from .models import GalleryItem


class GalleryImageInline(
    admin.TabularInline
):

    model = GalleryImage

    extra = 1

    fields = (
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

    def image_preview(self, obj):

        if (
            obj
            and obj.image
        ):

            try:

                return format_html(
                    '<img src="{}" '
                    'style="width:100px;height:75px;'
                    'object-fit:cover;border-radius:8px;" />',
                    obj.image.url,
                )

            except Exception:

                return "Unable to preview"

        return "No image"

    image_preview.short_description = (
        "Preview"
    )


@admin.register(GalleryItem)
class GalleryItemAdmin(
    admin.ModelAdmin
):

    form = GalleryItemForm

    inlines = [
        GalleryImageInline
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
        "additional_image_count",
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
            "Images",
            {
                "fields": (
                    "before_image",
                    "after_image",
                    "image",
                    "additional_images",
                    "gallery_preview",
                )
            },
        ),

        (
            "Details",
            {
                "fields": (
                    "description",
                    "featured",
                    "job_photo",
                    "job_photo_link",
                    "additional_image_count",
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

    # --------------------------------------------------------
    # Gallery preview
    # --------------------------------------------------------

    def _build_gallery_media_html(
        self,
        obj,
        thumb_size=60,
        max_items=None,
    ):

        media = list(
            obj.gallery_media
        )

        if not media:
            return "No image"

        if max_items is None:

            max_items = len(media)

        html_parts = [
            '<div style="display:flex;'
            'gap:8px;flex-wrap:wrap;'
            'align-items:flex-start;">'
        ]

        for item in media[
            :max_items
        ]:

            if item["is_image"]:

                html_parts.append(
                    format_html(
                        '<div>'
                        '<img src="{}" '
                        'width="{}" '
                        'height="{}" '
                        'style="object-fit:cover;'
                        'border-radius:6px;" />'
                        '</div>',
                        item["url"],
                        thumb_size,
                        thumb_size,
                    )
                )

            else:

                html_parts.append(
                    format_html(
                        '<div style="min-width:150px;'
                        'padding:12px;'
                        'border:1px solid #ddd;'
                        'border-radius:6px;">'
                        '<strong>{}</strong><br>'
                        '<a href="{}" '
                        'target="_blank">'
                        'Open file</a>'
                        '</div>',
                        item["name"],
                        item["url"],
                    )
                )

        if len(media) > max_items:

            html_parts.append(
                '<span style="align-self:center;'
                'color:#666;font-size:12px;">'
                '+ more'
                '</span>'
            )

        html_parts.append(
            "</div>"
        )

        return mark_safe(
            "".join(html_parts)
        )

    # --------------------------------------------------------
    # List preview
    # --------------------------------------------------------

    def image_preview(self, obj):

        return self._build_gallery_media_html(
            obj,
            thumb_size=60,
            max_items=4,
        )

    image_preview.short_description = (
        "Preview"
    )

    # --------------------------------------------------------
    # Full preview
    # --------------------------------------------------------

    def gallery_preview(self, obj):

        return self._build_gallery_media_html(
            obj,
            thumb_size=150,
            max_items=None,
        )

    gallery_preview.short_description = (
        "Gallery Preview"
    )

    # --------------------------------------------------------
    # Additional image count
    # --------------------------------------------------------

    def additional_image_count(
        self,
        obj
    ):

        if not obj or not obj.pk:
            return 0

        return obj.additional_images.count()

    additional_image_count.short_description = (
        "Additional Images"
    )

    # --------------------------------------------------------
    # Job photo link
    # --------------------------------------------------------

    def job_photo_link(
        self,
        obj
    ):

        if obj.job_photo:

            url = (
                "/admin/bookings/"
                "jobphoto/"
                f"{obj.job_photo.id}/"
                "change/"
            )

            return format_html(
                '<a href="{}" '
                'target="_blank">'
                'View Job Photo →'
                '</a>',
                url,
            )

        return "Not linked to job photo"

    job_photo_link.short_description = (
        "Linked Job Photo"
    )

    # --------------------------------------------------------
    # Delete button
    # --------------------------------------------------------

    def delete_action(
        self,
        obj
    ):

        return format_html(
            '<a class="button" '
            'style="background-color:#d4534f;" '
            'href="/admin/gallery/'
            'galleryitem/{}/delete/">'
            'Delete'
            '</a>',
            obj.pk,
        )

    delete_action.short_description = (
        "Action"
    )

    # --------------------------------------------------------
    # Readonly source when linked to JobPhoto
    # --------------------------------------------------------

    def get_readonly_fields(
        self,
        request,
        obj=None
    ):

        readonly = list(
            self.readonly_fields
        )

        if (
            obj
            and obj.job_photo
            and "source" not in readonly
        ):

            readonly.append(
                "source"
            )

        return readonly