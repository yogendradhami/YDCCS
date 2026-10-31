# ====================================================
# YD Commercial Cleaning Services
# File: employees/models.py
# Purpose:
# - Store cleaner/employee records
# - Link employees to login accounts
# - Track availability and performance
# ====================================================

import uuid

from django.contrib.auth.models import User
from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [
        ("cleaner", "Cleaner"),
        ("supervisor", "Supervisor"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    ]

    AVAILABILITY_CHOICES = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
        ("on_leave", "On Leave"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to="employees/",
        blank=True,
        null=True,
        help_text="Professional employee photo displayed on the public Team page.",
    )

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="cleaner")

    availability = models.CharField(
        max_length=30, choices=AVAILABILITY_CHOICES, default="available"
    )

    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=35)

    jobs_completed = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class SupplyRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        PARTIALLY_APPROVED = "partially_approved", "Partially approved"
        REJECTED = "rejected", "Rejected"
        PARTIALLY_ISSUED = "partially_issued", "Partially issued"
        ISSUED = "issued", "Issued"

    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="supply_requests",
    )
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    job_location = models.CharField(max_length=255)
    reason = models.TextField()
    urgency = models.CharField(
        max_length=12,
        choices=Urgency.choices,
        default=Urgency.NORMAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    decision_comments = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_supply_requests",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at", "-pk"]
        permissions = [
            ("manage_supply_requests", "Can approve and issue employee supply requests"),
        ]

    def __str__(self):
        return f"Supply request #{self.pk} from {self.employee.full_name}"


class SupplyRequestItem(models.Model):
    request = models.ForeignKey(
        SupplyRequest,
        on_delete=models.CASCADE,
        related_name="items",
    )
    supply = models.ForeignKey(
        "dashboard.CleaningSupply",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employee_request_items",
    )
    equipment = models.ForeignKey(
        "dashboard.Equipment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employee_request_items",
    )
    requested_quantity = models.PositiveIntegerField()
    approved_quantity = models.PositiveIntegerField(default=0)
    issued_quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=30)
    approval_comment = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(supply__isnull=False, equipment__isnull=True)
                    | models.Q(supply__isnull=True, equipment__isnull=False)
                ),
                name="supply_request_item_one_asset",
            ),
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gt=0),
                name="supply_request_item_positive_quantity",
            ),
            models.CheckConstraint(
                condition=models.Q(issued_quantity__lte=models.F("approved_quantity")),
                name="supply_request_item_issued_lte_approved",
            ),
            models.UniqueConstraint(
                fields=["request", "supply"],
                condition=models.Q(supply__isnull=False),
                name="unique_supply_per_employee_request",
            ),
            models.UniqueConstraint(
                fields=["request", "equipment"],
                condition=models.Q(equipment__isnull=False),
                name="unique_equipment_per_employee_request",
            ),
        ]

    @property
    def item_name(self):
        return self.supply.name if self.supply_id else self.equipment.name

    @property
    def remaining_to_issue(self):
        return max(0, self.approved_quantity - self.issued_quantity)

    def __str__(self):
        return f"{self.item_name} requested on #{self.request_id}"


class SupplyRequestAttachment(models.Model):
    request = models.ForeignKey(
        SupplyRequest,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="employee_supply_requests/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at", "pk"]

    def __str__(self):
        return self.original_filename


class EmployeeGoogleAccount(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="google_calendar_account",
    )

    email = models.EmailField(blank=True)

    access_token = models.TextField()

    refresh_token = models.TextField(blank=True, null=True)

    connected_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email:
            return f"{self.employee.full_name} - {self.email}"

        return f"{self.employee.full_name} - Google Calendar"


class PropertyDamageReport(models.Model):
    """Damage reported by an employee for one of their assigned bookings."""

    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Resolved & closed"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_damage_reports",
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_damage_reports",
    )
    description = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        db_index=True,
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_property_damage_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Property damage report #{self.pk}"


class PropertyDamageReportReply(models.Model):
    report = models.ForeignKey(
        PropertyDamageReport,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    responder = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_damage_report_replies",
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"Reply to property damage report #{self.report_id}"


class PropertyDamageReportPresence(models.Model):
    report = models.ForeignKey(
        PropertyDamageReport,
        on_delete=models.CASCADE,
        related_name="conversation_presence",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="property_damage_report_presence",
    )
    is_typing = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "user"],
                name="unique_damage_report_presence_per_user",
            )
        ]

    def __str__(self):
        return f"Presence for property damage report #{self.report_id}"


class PropertyDamageImage(models.Model):
    report = models.ForeignKey(
        PropertyDamageReport,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="damage_reports/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at", "pk"]

    def __str__(self):
        return f"Image for property damage report #{self.report_id}"