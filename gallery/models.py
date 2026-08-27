# ============================================================
# YD Commercial Cleaning Services
# File: gallery/models.py
# ============================================================

import logging
import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import models


# Optional HEIF/HEIC support
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass


class GalleryItem(models.Model):

    SERVICE_CHOICES = [
        ("Commercial Cleaning", "Commercial Cleaning"),
        ("Office Cleaning", "Office Cleaning"),
        ("House Cleaning", "House Cleaning"),
        ("Regular Cleaning", "Regular Cleaning"),
        ("End of Lease Cleaning", "End of Lease Cleaning"),
        ("Bond Cleaning", "Bond Cleaning"),
        ("Deep Cleaning", "Deep Cleaning"),
        ("Bathroom Deep Cleaning", "Bathroom Deep Cleaning"),
        ("Kitchen Deep Cleaning", "Kitchen Deep Cleaning"),
        ("Carpet Steam Cleaning", "Carpet Steam Cleaning"),
        ("Window & Glass Cleaning", "Window & Glass Cleaning"),
        ("Oven Cleaning", "Oven Cleaning"),
        ("Post Construction Cleaning", "Post Construction Cleaning"),
        ("Builders Cleaning", "Builders Cleaning"),
        ("Pressure Washing", "Pressure Washing"),
        ("Retail Cleaning", "Retail Cleaning"),
        ("Warehouse Cleaning", "Warehouse Cleaning"),
        ("School & Childcare Cleaning", "School & Childcare Cleaning"),
        ("Medical Cleaning", "Medical Cleaning"),
    ]

    SOURCE_CHOICES = [
        ("admin", "Admin Upload"),
        ("job_photo", "Job Photo"),
        ("customer", "Customer Upload"),
        ("employee", "Employee Upload"),
        ("booking", "Booking Form"),
        ("manual", "Manual Upload"),
    ]

    title = models.CharField(
        max_length=150
    )

    service_type = models.CharField(
        max_length=100,
        choices=SERVICE_CHOICES
    )

    suburb = models.CharField(
        max_length=100,
        blank=True
    )

    # --------------------------------------------------------
    # Before / After
    # --------------------------------------------------------

    before_image = models.ImageField(
        upload_to="gallery/before/",
        null=True,
        blank=True,
    )

    after_image = models.ImageField(
        upload_to="gallery/after/",
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # Original single generic image
    # --------------------------------------------------------

    image = models.ImageField(
        upload_to="gallery/uploads/",
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True
    )

    featured = models.BooleanField(
        default=True
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="manual"
    )

    # --------------------------------------------------------
    # Optional Job Photo link
    # --------------------------------------------------------

    job_photo = models.ForeignKey(
        "bookings.JobPhoto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_items",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    # --------------------------------------------------------
    # Primary image
    # --------------------------------------------------------

    @property
    def primary_image(self):
        """
        Main image used when there is no before/after pair.
        """

        if self.after_image:
            return self.after_image

        if self.image:
            return self.image

        return self.before_image

    # --------------------------------------------------------
    # Safe media helper
    # --------------------------------------------------------

    def _media_entry(self, field):

        if not field or not field.name:
            return None

        file_name = Path(field.name).name

        content_type, _ = mimetypes.guess_type(
            file_name
        )

        try:
            url = field.url

        except Exception:

            logger = logging.getLogger(__name__)

            try:
                logger.exception(
                    "GalleryItem: failed to resolve field.url "
                    "for %s (id=%s)",
                    file_name,
                    getattr(self, "id", None),
                )
            except Exception:
                pass

            url = (
                getattr(
                    settings,
                    "STATIC_URL",
                    "/static/"
                )
                + "images/services/placeholder.svg"
            )

        return {
            "url": url,
            "name": file_name,
            "is_image": (
                content_type.startswith("image/")
                if content_type
                else True
            ),
        }

    # --------------------------------------------------------
    # ALL gallery media
    # --------------------------------------------------------

    @property
    def gallery_media(self):

        media = []

        # Keep the existing order:
        #
        # 1. Generic image
        # 2. Before image
        # 3. After image
        # 4. Additional uploaded gallery images

        for field in [
            self.image,
            self.before_image,
            self.after_image,
        ]:

            if field and field.name:

                entry = self._media_entry(
                    field
                )

                if entry:
                    media.append(entry)

        # Additional multiple images
        for extra in self.additional_images.all():

            if extra.image and extra.image.name:

                entry = self._media_entry(
                    extra.image
                )

                if entry:
                    entry["id"] = extra.id
                    entry["order"] = extra.order
                    entry["additional"] = True

                    media.append(entry)

        return media

    # --------------------------------------------------------
    # Before media
    # --------------------------------------------------------

    @property
    def before_media(self):

        if (
            self.before_image
            and self.before_image.name
        ):

            return self._media_entry(
                self.before_image
            )

        return None

    # --------------------------------------------------------
    # After media
    # --------------------------------------------------------

    @property
    def after_media(self):

        if (
            self.after_image
            and self.after_image.name
        ):

            return self._media_entry(
                self.after_image
            )

        return None

    # --------------------------------------------------------
    # Gallery images
    # --------------------------------------------------------

    @property
    def gallery_images(self):

        images = []

        for img in [
            self.image,
            self.before_image,
            self.after_image,
        ]:

            if img and img.name:
                images.append(img)

        for extra in self.additional_images.all():

            if extra.image and extra.image.name:
                images.append(extra.image)

        return images


class GalleryImage(models.Model):
    """
    Additional images belonging to one GalleryItem.

    This allows one gallery card to contain unlimited
    additional images without changing the existing
    GalleryItem image fields.
    """

    gallery = models.ForeignKey(
        GalleryItem,
        on_delete=models.CASCADE,
        related_name="additional_images",
    )

    image = models.ImageField(
        upload_to="gallery/multiple/",
    )

    order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "order",
            "created_at",
            "id",
        ]

    def __str__(self):

        return (
            f"{self.gallery.title} "
            f"– Additional Image #{self.id}"
        )


