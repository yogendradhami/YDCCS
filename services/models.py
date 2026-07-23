from django.core.validators import FileExtensionValidator
from django.db import models


class Service(models.Model):
    slug = models.SlugField(
        help_text="URL-friendly identifier (e.g., 'commercial-cleaning')",
        max_length=100,
        unique=True,
    )
    name = models.CharField(
        help_text="Service name (e.g., 'Commercial Cleaning')",
        max_length=200,
    )
    description = models.TextField(help_text="Short service description for lists")
    overview = models.TextField(help_text="Longer overview for detail pages")
    hero_image = models.ImageField(
        help_text="Service hero image (recommended: 1200x800px)",
        upload_to="services/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )
    included = models.JSONField(default=list, help_text="List of included items/features")
    packages = models.JSONField(default=list, help_text="List of service packages with pricing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Services"
        ordering = ["name"]

    def __str__(self):
        return self.name
