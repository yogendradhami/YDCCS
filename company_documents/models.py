from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from .storage import CompanyDocumentStorage


class CompanyDocument(models.Model):
    """
    Central document repository for YD Commercial Cleaning.

    Supports documents belonging to:
    - Company
    - Employee
    - Customer
    - Vehicle
    - Supplier
    - Contract

    Files are stored in Cloudinary as RAW resources so that
    DOCX, XLSX, PPTX, ZIP and other non-image file types work correctly.
    """

    class Category(models.TextChoices):
        COMPANY = "company", "Company & Corporate"
        EMPLOYEE = "employee", "Employee & HR"
        CUSTOMER = "customer", "Customers & Clients"
        INSURANCE = "insurance", "Insurance"
        VEHICLE = "vehicle", "Vehicles & Fleet"
        CONTRACT = "contract", "Contracts & Agreements"
        WHS = "whs", "WHS & Compliance"
        FINANCE = "finance", "Finance & Tax"
        LICENCE = "licence", "Licences & Registrations"
        OPERATIONS = "operations", "Operations"
        SUPPLIER = "supplier", "Suppliers & Vendors"
        PROPERTY = "property", "Property & Premises"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    class RelatedType(models.TextChoices):
        COMPANY = "company", "Company"
        EMPLOYEE = "employee", "Employee"
        CUSTOMER = "customer", "Customer"
        VEHICLE = "vehicle", "Vehicle"
        SUPPLIER = "supplier", "Supplier"
        CONTRACT = "contract", "Contract"

    # ==========================================================
    # BASIC DOCUMENT INFORMATION
    # ==========================================================

    name = models.CharField(
        max_length=255,
        db_index=True,
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )

    document_type = models.CharField(
        max_length=150,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    document_reference = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )

    # ==========================================================
    # FILE
    # ==========================================================

    file = models.FileField(
        storage=CompanyDocumentStorage(),
        upload_to="company_documents/%Y/%m/",
        max_length=500,
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    mime_type = models.CharField(
        max_length=255,
        blank=True,
    )

    # ==========================================================
    # DATES
    # ==========================================================

    issue_date = models.DateField(
        blank=True,
        null=True,
    )

    expiry_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
    )

    review_date = models.DateField(
        blank=True,
        null=True,
    )

    # ==========================================================
    # SECURITY / STATUS
    # ==========================================================

    is_sensitive = models.BooleanField(
        default=False,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    # ==========================================================
    # RELATIONSHIP
    # ==========================================================

    related_type = models.CharField(
        max_length=20,
        choices=RelatedType.choices,
        default=RelatedType.COMPANY,
        db_index=True,
    )

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_documents",
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_documents",
    )

    vehicle = models.ForeignKey(
        "dashboard.Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_documents",
    )

    supplier = models.ForeignKey(
        "dashboard.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_documents",
    )

    contract = models.ForeignKey(
        "contracts.CleaningContract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_documents",
    )

    # ==========================================================
    # VERSIONING
    # ==========================================================

    version = models.PositiveIntegerField(
        default=1,
    )

    previous_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_versions",
    )

    # ==========================================================
    # OWNERSHIP / AUDIT
    # ==========================================================

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_company_documents",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ==========================================================
    # META
    # ==========================================================

    class Meta:
        ordering = ["-updated_at"]

        permissions = [
            (
                "email_companydocument",
                "Can email company documents",
            ),
            (
                "download_sensitive_companydocument",
                "Can download sensitive company documents",
            ),
        ]

    # ==========================================================
    # STRING
    # ==========================================================

    def __str__(self):
        return self.name

    # ==========================================================
    # EXPIRY STATUS
    # ==========================================================

    @property
    def calculated_status(self):
        """
        Returns the current operational status:

        active
        expiring
        expired
        archived
        """

        if self.status == self.Status.ARCHIVED:
            return "archived"

        if not self.expiry_date:
            return "active"

        today = timezone.localdate()

        if self.expiry_date < today:
            return "expired"

        if self.expiry_date <= today + timedelta(days=30):
            return "expiring"

        return "active"

    @property
    def status_label(self):
        return {
            "active": "Active",
            "expiring": "Expiring Soon",
            "expired": "Expired",
            "archived": "Archived",
        }.get(
            self.calculated_status,
            "Active",
        )

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None

        return (
            self.expiry_date - timezone.localdate()
        ).days

    # ==========================================================
    # RELATED OBJECT
    # ==========================================================

    @property
    def related_object(self):
        mapping = {
            self.RelatedType.EMPLOYEE: self.employee,
            self.RelatedType.CUSTOMER: self.customer,
            self.RelatedType.VEHICLE: self.vehicle,
            self.RelatedType.SUPPLIER: self.supplier,
            self.RelatedType.CONTRACT: self.contract,
        }

        if self.related_type == self.RelatedType.COMPANY:
            return None

        return mapping.get(self.related_type)

    @property
    def related_name(self):
        """
        Human-readable relationship name for the dashboard.
        """

        if self.related_type == self.RelatedType.COMPANY:
            return "YD Commercial Cleaning"

        obj = self.related_object

        if obj is None:
            return "—"

        if self.related_type == self.RelatedType.EMPLOYEE:
            return obj.full_name

        if self.related_type == self.RelatedType.CUSTOMER:
            return obj.full_name

        if self.related_type == self.RelatedType.VEHICLE:
            return (
                f"{obj.vehicle_name} "
                f"({obj.registration_number})"
            )

        if self.related_type == self.RelatedType.SUPPLIER:
            return obj.name

        if self.related_type == self.RelatedType.CONTRACT:
            return (
                f"{obj.customer.full_name} "
                f"— {obj.service_type}"
            )

        return str(obj)


class CompanyDocumentAudit(models.Model):
    """
    Audit trail for Company Documents.
    """

    class Action(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        VIEWED = "viewed", "Viewed"
        DOWNLOADED = "downloaded", "Downloaded"
        EMAILED = "emailed", "Emailed"
        UPDATED = "updated", "Updated"
        VERSION_REPLACED = (
            "version_replaced",
            "Version Replaced",
        )
        ARCHIVED = "archived", "Archived"
        RESTORED = "restored", "Restored"

    document = models.ForeignKey(
        CompanyDocument,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_document_audit_events",
    )

    action = models.CharField(
        max_length=40,
        choices=Action.choices,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.document} - {self.action}"
        )