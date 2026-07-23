# ==========================================================
# File: dashboard/models.py
# Purpose:
# - Company settings used throughout the website
# - Activity log for tracking important CRM actions
# ==========================================================

from django.contrib.auth.models import User
from django.db import models


def site_image_upload_path(instance, filename):
    """Generate upload path for site images."""
    return f"site_images/{instance.name}/{filename}"


class CompanySettings(models.Model):
    """
    Global company settings.
    Only one record should normally exist.
    """

    # ======================================================
    # Business Information
    # ======================================================

    business_name = models.CharField(
        max_length=255, default="YD Commercial Cleaning Services"
    )

    abn = models.CharField(max_length=50, blank=True)

    phone = models.CharField(max_length=50, blank=True)

    email = models.EmailField(blank=True)

    website = models.URLField(blank=True)

    address = models.TextField(blank=True)

    # ======================================================
    # Branding
    # ======================================================

    logo = models.ImageField(upload_to="company/", blank=True, null=True)

    favicon = models.ImageField(upload_to="company/", blank=True, null=True)

    # ======================================================
    # Social Media
    # ======================================================

    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    # ======================================================
    # Invoice Settings
    # ======================================================

    invoice_prefix = models.CharField(max_length=20, default="YD")

    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    payment_terms_days = models.PositiveIntegerField(default=7)

    # ======================================================
    # Timestamps
    # ======================================================

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name


class ActivityLog(models.Model):
    """
    Tracks important CRM actions.
    Example:
    - Booking created
    - Invoice paid
    - Payroll generated
    - Leave approved
    - Settings updated
    """

    ACTION_TYPES = [
        ("booking", "Booking"),
        ("invoice", "Invoice"),
        ("customer", "Customer"),
        ("employee", "Employee"),
        ("payroll", "Payroll"),
        ("leave", "Leave"),
        ("roster", "Roster"),
        ("settings", "Settings"),
        ("system", "System"),
    ]

    # User who performed the action.
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Category of action.
    action_type = models.CharField(
        max_length=30, choices=ACTION_TYPES, default="system"
    )

    # Short title shown in activity table.
    title = models.CharField(max_length=200)

    # Longer explanation of the action.
    description = models.TextField(blank=True)

    # Time action happened.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

# Email Log
# Tracks emails sent from the CRM Email Center.
# ==========================================================


class EmailLog(models.Model):
    EMAIL_TYPES = [
        ("invoice_reminder", "Invoice Reminder"),
        ("booking_reminder", "Booking Reminder"),
        ("quote_followup", "Quote Follow-up"),
        ("contract_renewal", "Contract Renewal"),
        ("vip_campaign", "VIP Campaign"),
        ("system", "System"),
    ]

    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES, default="system")

    recipient_name = models.CharField(max_length=150)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    related_object = models.CharField(max_length=150, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} → {self.recipient_email}"

# Review Request Log
# Tracks Google review request emails sent to customers.
# ==========================================================


class ReviewRequestLog(models.Model):
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="review_request_log"
    )

    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    sent_count = models.PositiveIntegerField(default=0)

    last_sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review request for booking #{self.booking.id}"


class CampaignLog(models.Model):
    CAMPAIGN_TYPES = [
        ("vip", "VIP Customer Campaign"),
        ("inactive", "Inactive Customer Campaign"),
        ("review", "Review Follow-up Campaign"),
    ]

    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    campaign_type = models.CharField(max_length=50, choices=CAMPAIGN_TYPES)

    title = models.CharField(max_length=200)
    recipients_count = models.PositiveIntegerField(default=0)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.title} - {self.recipients_count} recipients"


# ==========================================================
# Equipment Inventory
# ==========================================================


class Equipment(models.Model):

    CONDITION_CHOICES = [
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("repair", "Needs Repair"),
        ("retired", "Retired"),
    ]

    name = models.CharField(max_length=200)

    serial_number = models.CharField(max_length=100, blank=True)

    purchase_date = models.DateField(null=True, blank=True)

    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    assigned_employee = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True
    )

    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, default="good"
    )

    next_service_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==========================================================
# Careers / Applications
# ==========================================================


class CareerApplication(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to="careers/resumes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

class CleaningSupply(models.Model):

    UNIT_CHOICES = [
        ("bottle", "Bottle"),
        ("litre", "Litre"),
        ("box", "Box"),
        ("pack", "Pack"),
        ("piece", "Piece"),
        ("roll", "Roll"),
    ]

    name = models.CharField(max_length=200)

    category = models.CharField(max_length=100, blank=True)

    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=5)

    unit = models.CharField(max_length=30, choices=UNIT_CHOICES, default="piece")

    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    supplier_name = models.CharField(max_length=150, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock

    def total_value(self):
        return self.current_stock * self.unit_cost

    def __str__(self):
        return self.name


# ==========================================================
# Purchase Orders
# ==========================================================


class PurchaseOrder(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("ordered", "Ordered"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]

    supply = models.ForeignKey("dashboard.CleaningSupply", on_delete=models.CASCADE)

    supplier_name = models.CharField(max_length=150)

    quantity = models.PositiveIntegerField()

    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    order_date = models.DateField(auto_now_add=True)

    notes = models.TextField(blank=True)

    def total_cost(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"PO #{self.id}"


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    abn = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Vehicle(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    ]

    vehicle_name = models.CharField(max_length=150)

    registration_number = models.CharField(max_length=50, unique=True)

    make = models.CharField(max_length=100, blank=True)

    model = models.CharField(max_length=100, blank=True)

    year = models.PositiveIntegerField(null=True, blank=True)

    assigned_employee = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True
    )

    insurance_expiry = models.DateField(null=True, blank=True)

    registration_expiry = models.DateField(null=True, blank=True)

    service_due_date = models.DateField(null=True, blank=True)

    odometer = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_name} ({self.registration_number})"


class MaintenanceHistory(models.Model):

    # Duplicate block removed (fields/methods already defined above)

    ASSET_TYPE_CHOICES = [
        ("vehicle", "Vehicle"),
        ("equipment", "Equipment"),
    ]

    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES)

    asset_name = models.CharField(max_length=200)

    maintenance_date = models.DateField()

    next_service_date = models.DateField(null=True, blank=True)

    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    performed_by = models.CharField(max_length=200, blank=True)

    description = models.TextField()

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset_name} - {self.maintenance_date}"


class SiteImage(models.Model):
    """Store images used across the site (hero banners, backgrounds, etc.)"""

    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=50,
        choices=[
            ("hero", "Hero / Homepage"),
            ("blog", "Blog Post"),
            ("service", "Service Page"),
            ("company", "Company / Logo"),
            ("team", "Team / Staff"),
            ("other", "Other"),
        ],
        default="other",
    )

    image = models.ImageField(upload_to=site_image_upload_path)
    description = models.TextField(blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    @property
    def name(self):
        return self.title
    # Keep `uploaded_at` to match existing migration (0014_siteimage.py)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    @property
    def created_at(self):
        return self.uploaded_at
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
