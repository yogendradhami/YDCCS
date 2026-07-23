# ====================================================
# YD Commercial Cleaning Services
# File: quotes/models.py
# Purpose: Quote request database models
# ====================================================

from django.db import models


class QuoteRequest(models.Model):
    # -------------------------------
    # Property type dropdown options
    # -------------------------------
    PROPERTY_TYPES = [
        ("", "– Select property type –"),
        ("House", "House"),
        ("Apartment", "Apartment"),
        ("Office", "Office"),
        ("Commercial Property", "Commercial Property"),
        ("End of Lease Property", "End of Lease Property"),
        ("Other", "Other"),
    ]

    # -------------------------------
    # Lead status options
    # Used for dashboard/CRM tracking
    # -------------------------------
    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("quoted", "Quoted"),
        ("booked", "Booked"),
        ("completed", "Completed"),
        ("lost", "Lost"),
    ]

    LEAD_SOURCE_CHOICES = [
        ("website", "Website"),
        ("google", "Google Business Profile"),
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("tiktok", "TikTok"),
        ("hipages", "Hipages"),
        ("referral", "Referral"),
        ("other", "Other"),
    ]

    # -------------------------------
    # Customer details
    # -------------------------------
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    lead_source = models.CharField(
        max_length=50, choices=LEAD_SOURCE_CHOICES, default="website"
    )

    # -------------------------------
    # Property and booking details
    # -------------------------------
    property_type = models.CharField(max_length=100, choices=PROPERTY_TYPES)
    suburb_postcode = models.CharField(max_length=150)
    preferred_date = models.DateField(null=True, blank=True)
    message = models.TextField(blank=True)

    # AI estimator
    bedrooms = models.PositiveIntegerField(default=1)

    bathrooms = models.PositiveIntegerField(default=1)

    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # -------------------------------
    # Add-on cleaning services
    # -------------------------------
    window_cleaning = models.BooleanField(default=False)
    carpet_shampooing = models.BooleanField(default=False)
    grout_cleaning = models.BooleanField(default=False)
    upholstery_cleaning = models.BooleanField(default=False)
    laundry_service = models.BooleanField(default=False)

    # -------------------------------
    # Simple anti-spam checkbox
    # -------------------------------
    is_not_robot = models.BooleanField(default=False)

    # -------------------------------
    # Lead management status
    # -------------------------------
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    # -------------------------------
    # Admin notes for follow-up
    # -------------------------------
    admin_notes = models.TextField(blank=True)

    # -------------------------------
    # Timestamp
    # -------------------------------
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.property_type} - {self.status}"


class QuoteImage(models.Model):
    # -------------------------------
    # Multiple uploaded images
    # linked to one quote request
    # -------------------------------
    quote = models.ForeignKey(
        QuoteRequest, on_delete=models.CASCADE, related_name="images"
    )

    image = models.ImageField(upload_to="quote_images/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.quote.name}"
