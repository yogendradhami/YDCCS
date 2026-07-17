from django.db import models
<<<<<<< HEAD

# Create your models here.
=======
from django.core.validators import FileExtensionValidator

class Service(models.Model):
    """Service model with image upload and metadata"""
    
    slug = models.SlugField(unique=True, max_length=100, help_text="URL-friendly identifier (e.g., 'commercial-cleaning')")
    name = models.CharField(max_length=200, help_text="Service name (e.g., 'Commercial Cleaning')")
    description = models.TextField(help_text="Short service description for lists")
    overview = models.TextField(help_text="Longer overview for detail pages")
    
    # Image upload with validation
    hero_image = models.ImageField(
        upload_to='services/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Service hero image (recommended: 1200x800px)"
    )
    
    # Structured data
    included = models.JSONField(default=list, help_text="List of included items/features")
    packages = models.JSONField(default=list, help_text="List of service packages with pricing")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Services'
    
    def __str__(self):
        return self.name
>>>>>>> 5815f15 (Initial project commit)
