from django.db import models
<<<<<<< HEAD

# Create your models here.
=======
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Store blog images under project static/uploads/blog/
static_fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR, "static"), base_url=settings.STATIC_URL)


def blog_upload_path(instance, filename):
    return os.path.join("uploads", "blog", filename)


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()

    featured_image = models.ImageField(upload_to=blog_upload_path, storage=static_fs, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True)
    published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title
>>>>>>> 5815f15 (Initial project commit)
