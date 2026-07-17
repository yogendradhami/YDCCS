<<<<<<< HEAD
=======
from django.db import models

>>>>>>> 5815f15 (Initial project commit)
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

    title = models.CharField(max_length=150)
    service_type = models.CharField(max_length=100, choices=SERVICE_CHOICES)
    suburb = models.CharField(max_length=100, blank=True)

    before_image = models.ImageField(upload_to="gallery/before/")
    after_image = models.ImageField(upload_to="gallery/after/")

    description = models.TextField(blank=True)
    featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
<<<<<<< HEAD
        return self.title
=======
        return self.title
>>>>>>> 5815f15 (Initial project commit)
