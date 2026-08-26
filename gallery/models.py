# gallery/models.py

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

    title = models.CharField(max_length=150)

    service_type = models.CharField(
        max_length=100,
        choices=SERVICE_CHOICES,
    )

    suburb = models.CharField(
        max_length=100,
        blank=True,
    )

    # Existing main gallery images
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

    # Existing generic gallery image
    image = models.ImageField(
        upload_to="gallery/uploads/",
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    featured = models.BooleanField(
        default=True,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="manual",
    )

    # Optional link to job photo source
    job_photo = models.ForeignKey(
        "bookings.JobPhoto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_items",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def primary_image(self):
        """
        Return the main image.
        Priority:
        generic image -> after image -> before image -> additional media.
        """
        if self.image:
            return self.image

        if self.after_image:
            return self.after_image

        if self.before_image:
            return self.before_image

        additional = self.media_files.filter(
            media_type="image"
        ).first()

        if additional and additional.image:
            return additional.image

        return None

    def _media_entry(self, field):
        """
        Safely return media information without forcing
        Cloudinary access until required.
        """

        if not field or not field.name:
            return None

        file_name = Path(field.name).name

        content_type, _ = mimetypes.guess_type(file_name)

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
                getattr(settings, "STATIC_URL", "/static/")
                + "images/placeholder.svg"
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

    @property
    def gallery_media(self):
        """
        Return ALL images belonging to this gallery section.

        This includes:
        1. Existing generic image
        2. Existing before image
        3. Existing after image
        4. Unlimited additional GalleryMedia images
        """

        media = []

        # Existing image fields
        for field in [
            self.image,
            self.before_image,
            self.after_image,
        ]:
            if field and field.name:
                entry = self._media_entry(field)

                if entry:
                    media.append(entry)

        # Additional uploaded gallery images
        try:
            additional_media = self.media_files.filter(
                media_type="image"
            ).order_by(
                "order",
                "created_at",
            )

            for media_file in additional_media:
                if media_file.image and media_file.image.name:
                    entry = self._media_entry(media_file.image)

                    if entry:
                        media.append(entry)

        except Exception:
            # Keeps existing gallery pages safe if media records
            # are unavailable during migration/deployment.
            pass

        return media

    @property
    def before_media(self):
        if self.before_image and self.before_image.name:
            return self._media_entry(self.before_image)

        return None

    @property
    def after_media(self):
        if self.after_image and self.after_image.name:
            return self._media_entry(self.after_image)

        return None

    @property
    def gallery_images(self):
        """
        Return actual image fields/files belonging to this gallery.
        """

        images = []

        for img in [
            self.image,
            self.before_image,
            self.after_image,
        ]:
            if img and img.name:
                images.append(img)

        try:
            additional_media = self.media_files.filter(
                media_type="image"
            ).order_by(
                "order",
                "created_at",
            )

            for media_file in additional_media:
                if media_file.image and media_file.image.name:
                    images.append(media_file.image)

        except Exception:
            pass

        return images


class GalleryMedia(models.Model):
    """
    Additional media belonging to a GalleryItem.

    One GalleryItem can have unlimited GalleryMedia records.
    """

    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
    ]

    VIDEO_PLATFORM_CHOICES = [
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
    ]

    gallery = models.ForeignKey(
        GalleryItem,
        on_delete=models.CASCADE,
        related_name="media_files",
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES,
        default="image",
    )

    image = models.ImageField(
        upload_to="gallery/media/images/",
        null=True,
        blank=True,
    )

    video_platform = models.CharField(
        max_length=20,
        choices=VIDEO_PLATFORM_CHOICES,
        null=True,
        blank=True,
    )

    video_url = models.URLField(
        null=True,
        blank=True,
    )

    video_thumbnail = models.ImageField(
        upload_to="gallery/media/thumbnails/",
        null=True,
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "order",
            "created_at",
        ]

    def __str__(self):
        if self.image:
            return f"{self.gallery.title} - {Path(self.image.name).name}"

        return f"{self.gallery.title} - Media #{self.pk}"

    @property
    def media_url(self):
        """
        Safely return the image/video URL.
        """

        if self.media_type == "image" and self.image:
            try:
                return self.image.url
            except Exception:
                return None

        if self.video_url:
            return self.video_url

        return None