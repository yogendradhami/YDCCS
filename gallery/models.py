# Create your models here.
from django.db import models


class GalleryItem(models.Model):
    SERVICE_CHOICES = [
        ("Commercial Cleaning", "Commercial Cleaning"),
        ("Office Cleaning", "Office Cleaning"),
        ("House Cleaning", "House Cleaning"),
        ("End of Lease Cleaning", "End of Lease Cleaning"),
        ("Window Cleaning", "Window Cleaning"),
        ("Deep Cleaning", "Deep Cleaning"),
        ("Post Construction Cleaning", "Post Construction Cleaning"),
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
    before_image = models.FileField(
        upload_to="gallery/before/",
        null=True,
        blank=True,
    )
    after_image = models.FileField(
        upload_to="gallery/after/",
        null=True,
        blank=True,
    )

    # Single image for generic gallery uploads
    image = models.FileField(
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

    @property
    def gallery_images(self):
        images = []
        if self.image:
            images.append(self.image)
        if self.before_image:
            images.append(self.before_image)
        if self.after_image:
            images.append(self.after_image)
        return images
