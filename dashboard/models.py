# ==========================================================
# File: dashboard/models.py
# Purpose:
# - Company settings used throughout the website
# - Activity log for tracking important CRM actions
# ==========================================================

<<<<<<< HEAD
from django.contrib.auth.models import User
from django.db import models
=======
from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
>>>>>>> 5815f15 (Initial project commit)


class CompanySettings(models.Model):
    """
    Global company settings.
    Only one record should normally exist.
    """

    # ======================================================
    # Business Information
    # ======================================================

    business_name = models.CharField(
<<<<<<< HEAD
        max_length=255, default="YD Commercial Cleaning Services"
    )

    abn = models.CharField(max_length=50, blank=True)

    phone = models.CharField(max_length=50, blank=True)

    email = models.EmailField(blank=True)

    website = models.URLField(blank=True)

    address = models.TextField(blank=True)
=======
        max_length=255,
        default="YD Commercial Cleaning Services"
    )

    abn = models.CharField(
        max_length=50,
        blank=True
    )

    phone = models.CharField(
        max_length=50,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    address = models.TextField(
        blank=True
    )
>>>>>>> 5815f15 (Initial project commit)

    # ======================================================
    # Branding
    # ======================================================

<<<<<<< HEAD
    logo = models.ImageField(upload_to="company/", blank=True, null=True)

    favicon = models.ImageField(upload_to="company/", blank=True, null=True)
=======
    logo = models.ImageField(
        upload_to="company/",
        blank=True,
        null=True
    )

    favicon = models.ImageField(
        upload_to="company/",
        blank=True,
        null=True
    )
>>>>>>> 5815f15 (Initial project commit)

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

<<<<<<< HEAD
    invoice_prefix = models.CharField(max_length=20, default="YD")

    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    payment_terms_days = models.PositiveIntegerField(default=7)
=======
    invoice_prefix = models.CharField(
        max_length=20,
        default="YD"
    )

    gst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00
    )

    payment_terms_days = models.PositiveIntegerField(
        default=7
    )
>>>>>>> 5815f15 (Initial project commit)

    # ======================================================
    # Timestamps
    # ======================================================

<<<<<<< HEAD
    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
=======
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
>>>>>>> 5815f15 (Initial project commit)

    def __str__(self):
        return self.business_name


<<<<<<< HEAD
=======
# ==========================================================
# Site Images - upload site-wide images from dashboard
# Files are stored under <project_root>/static/uploads/<category>/
# ==========================================================

# Use a FileSystemStorage pointed at the project's static folder so uploads
# end up inside `static/uploads/...` as requested.
static_fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR, "static"), base_url=settings.STATIC_URL)


def site_image_upload_path(instance, filename):
    return os.path.join("uploads", instance.category, filename)


class SiteImage(models.Model):
    CATEGORY_CHOICES = [
        ("hero", "Hero / Homepage"),
        ("blog", "Blog Post"),
        ("service", "Service Page"),
        ("company", "Company / Logo"),
        ("team", "Team / Staff"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")

    image = models.ImageField(
        upload_to=site_image_upload_path,
        storage=static_fs,
        blank=False,
        null=False,
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} — {self.title}"


>>>>>>> 5815f15 (Initial project commit)
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
<<<<<<< HEAD
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
=======
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Category of action.
    action_type = models.CharField(
        max_length=30,
        choices=ACTION_TYPES,
        default="system"
    )

    # Short title shown in activity table.
    title = models.CharField(
        max_length=200
    )

    # Longer explanation of the action.
    description = models.TextField(
        blank=True
    )

    # Time action happened.
    created_at = models.DateTimeField(
        auto_now_add=True
    )
>>>>>>> 5815f15 (Initial project commit)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
<<<<<<< HEAD

    # ==========================================================


=======
    
    # ==========================================================
>>>>>>> 5815f15 (Initial project commit)
# Email Log
# Tracks emails sent from the CRM Email Center.
# ==========================================================

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
class EmailLog(models.Model):
    EMAIL_TYPES = [
        ("invoice_reminder", "Invoice Reminder"),
        ("booking_reminder", "Booking Reminder"),
        ("quote_followup", "Quote Follow-up"),
        ("contract_renewal", "Contract Renewal"),
        ("vip_campaign", "VIP Campaign"),
        ("system", "System"),
    ]

<<<<<<< HEAD
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES, default="system")
=======
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    email_type = models.CharField(
        max_length=50,
        choices=EMAIL_TYPES,
        default="system"
    )
>>>>>>> 5815f15 (Initial project commit)

    recipient_name = models.CharField(max_length=150)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    related_object = models.CharField(max_length=150, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} → {self.recipient_email}"
<<<<<<< HEAD

    # ==========================================================


=======
    
    # ==========================================================
>>>>>>> 5815f15 (Initial project commit)
# Review Request Log
# Tracks Google review request emails sent to customers.
# ==========================================================

<<<<<<< HEAD

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


=======
class ReviewRequestLog(models.Model):
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="review_request_log"
    )

    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    sent_count = models.PositiveIntegerField(
        default=0
    )

    last_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Review request for booking #{self.booking.id}"
    
>>>>>>> 5815f15 (Initial project commit)
class CampaignLog(models.Model):
    CAMPAIGN_TYPES = [
        ("vip", "VIP Customer Campaign"),
        ("inactive", "Inactive Customer Campaign"),
        ("review", "Review Follow-up Campaign"),
    ]

<<<<<<< HEAD
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    campaign_type = models.CharField(max_length=50, choices=CAMPAIGN_TYPES)
=======
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    campaign_type = models.CharField(
        max_length=50,
        choices=CAMPAIGN_TYPES
    )
>>>>>>> 5815f15 (Initial project commit)

    title = models.CharField(max_length=200)
    recipients_count = models.PositiveIntegerField(default=0)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.title} - {self.recipients_count} recipients"

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
# ==========================================================
# Equipment Inventory
# ==========================================================

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
class Equipment(models.Model):

    CONDITION_CHOICES = [
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("repair", "Needs Repair"),
        ("retired", "Retired"),
    ]

    name = models.CharField(max_length=200)

<<<<<<< HEAD
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


# Cleaning Supplies Inventory
# ==========================================================


=======
    serial_number = models.CharField(
        max_length=100,
        blank=True
    )

    purchase_date = models.DateField(
        null=True,
        blank=True
    )

    purchase_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    assigned_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default="good"
    )

    next_service_date = models.DateField(
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name
    

    # ==========================================================
# Cleaning Supplies Inventory
# ==========================================================

>>>>>>> 5815f15 (Initial project commit)
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

<<<<<<< HEAD
    category = models.CharField(max_length=100, blank=True)
=======
    category = models.CharField(
        max_length=100,
        blank=True
    )
>>>>>>> 5815f15 (Initial project commit)

    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=5)

<<<<<<< HEAD
    unit = models.CharField(max_length=30, choices=UNIT_CHOICES, default="piece")

    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    supplier_name = models.CharField(max_length=150, blank=True)
=======
    unit = models.CharField(
        max_length=30,
        choices=UNIT_CHOICES,
        default="piece"
    )

    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    supplier_name = models.CharField(
        max_length=150,
        blank=True
    )
>>>>>>> 5815f15 (Initial project commit)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock

    def total_value(self):
        return self.current_stock * self.unit_cost

    def __str__(self):
        return self.name
<<<<<<< HEAD


=======
    
>>>>>>> 5815f15 (Initial project commit)
# ==========================================================
# Purchase Orders
# ==========================================================

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
class PurchaseOrder(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("ordered", "Ordered"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]

<<<<<<< HEAD
    supply = models.ForeignKey("dashboard.CleaningSupply", on_delete=models.CASCADE)

    supplier_name = models.CharField(max_length=150)

    quantity = models.PositiveIntegerField()

    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
=======
    supply = models.ForeignKey(
        "dashboard.CleaningSupply",
        on_delete=models.CASCADE
    )

    supplier_name = models.CharField(
        max_length=150
    )

    quantity = models.PositiveIntegerField()

    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
>>>>>>> 5815f15 (Initial project commit)

    order_date = models.DateField(auto_now_add=True)

    notes = models.TextField(blank=True)

    def total_cost(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"PO #{self.id}"
<<<<<<< HEAD

=======
    
>>>>>>> 5815f15 (Initial project commit)

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
<<<<<<< HEAD

=======
    
>>>>>>> 5815f15 (Initial project commit)

class Vehicle(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    ]

    vehicle_name = models.CharField(max_length=150)

<<<<<<< HEAD
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

=======
    registration_number = models.CharField(
        max_length=50,
        unique=True
    )

    make = models.CharField(
        max_length=100,
        blank=True
    )

    model = models.CharField(
        max_length=100,
        blank=True
    )

    year = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    assigned_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    insurance_expiry = models.DateField(
        null=True,
        blank=True
    )

    registration_expiry = models.DateField(
        null=True,
        blank=True
    )

    service_due_date = models.DateField(
        null=True,
        blank=True
    )

    odometer = models.PositiveIntegerField(
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.vehicle_name} ({self.registration_number})"
    

class MaintenanceHistory(models.Model):

>>>>>>> 5815f15 (Initial project commit)
    ASSET_TYPE_CHOICES = [
        ("vehicle", "Vehicle"),
        ("equipment", "Equipment"),
    ]

<<<<<<< HEAD
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
=======
    asset_type = models.CharField(
        max_length=20,
        choices=ASSET_TYPE_CHOICES
    )

    asset_name = models.CharField(
        max_length=200
    )

    maintenance_date = models.DateField()

    next_service_date = models.DateField(
        null=True,
        blank=True
    )

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    performed_by = models.CharField(
        max_length=200,
        blank=True
    )

    description = models.TextField()

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.asset_name} - {self.maintenance_date}"


    ASSET_TYPE_CHOICES = [
        ("vehicle", "Vehicle"),
        ("equipment", "Equipment"),
    ]

    asset_type = models.CharField(
        max_length=20,
        choices=ASSET_TYPE_CHOICES
    )

    asset_name = models.CharField(
        max_length=200
    )

    maintenance_date = models.DateField()

    next_service_date = models.DateField(
        null=True,
        blank=True
    )

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    performed_by = models.CharField(
        max_length=200,
        blank=True
    )

    description = models.TextField()

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.asset_name} - {self.maintenance_date}"
>>>>>>> 5815f15 (Initial project commit)
