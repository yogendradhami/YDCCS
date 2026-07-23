from django.db import models


def blog_upload_path(instance, filename):
    """Generate upload path for blog featured images."""
    return f"blog/{instance.slug}/{filename}"


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    featured_image = models.ImageField(
        upload_to=blog_upload_path, blank=True, null=True
    )
    category = models.CharField(max_length=100, blank=True)
    published = models.BooleanField(default=True)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title
