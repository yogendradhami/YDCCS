# Create your models here.
import mimetypes
from pathlib import Path

# Optional HEIF/HEIC support — guard import so tests don't fail when library is missing
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    # pillow_heif not available in this environment; continue without HEIF support
    pass

from django.db import models
from django.conf import settings
import logging

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
    service_type = models.CharField(max_length=100, choices=SERVICE_CHOICES)
    suburb = models.CharField(max_length=100, blank=True)

    # Single or before/after images
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

    # Single image for generic gallery uploads
    image = models.ImageField(
        upload_to="gallery/uploads/",
        null=True,
        blank=True,
    )

    description = models.TextField(blank=True)
    featured = models.BooleanField(default=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")

    # Optional link to job photo source
    job_photo = models.ForeignKey(
        'bookings.JobPhoto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_items"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def primary_image(self):
        """Return the main image (before, after, or generic)"""
        if self.image:
            return self.image
        return self.after_image or self.before_image

    def _media_entry(self, field):
        """
        Safely return media information without forcing Cloudinary file access.
        """

        if not field or not field.name:
            return None

        file_name = Path(field.name).name

        content_type, _ = mimetypes.guess_type(file_name)
        # Accessing `field.url` can raise when the storage backend is
        # misconfigured or remote provider is unavailable (eg. Cloudinary).
        # Guard that call and fall back to a local placeholder so templates
        # do not error in production.
        try:
            url = field.url
        except Exception:
            logger = logging.getLogger(__name__)
            try:
                logger.exception("GalleryItem: failed to resolve field.url for %s (id=%s)", file_name, getattr(self, 'id', None))
            except Exception:
                logger.exception("GalleryItem: failed to resolve field.url and failed to log details")
            url = getattr(settings, 'STATIC_URL', '/static/') + 'images/placeholder.svg'

        return {
            "url": url,
            "name": file_name,
            "is_image": (
                content_type.startswith("image/") if content_type else True
            ),
        }

    @property
    def gallery_media(self):
        media = []

        for field in [
            self.image,
            self.before_image,
            self.after_image,
        ]:
            if field and field.name:
                entry = self._media_entry(field)

                if entry:
                    media.append(entry)

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
        images = []

        for img in [
            self.image,
            self.before_image,
            self.after_image,
        ]:
            if img and img.name:
                images.append(img)

        return images