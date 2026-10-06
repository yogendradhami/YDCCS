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

    file_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 hash of the uploaded file.",
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
    def health_status(self):
        """
        Return the current compliance health state of the document.

        Health states:
            inactive   - document is not active
            expired    - expiry date has passed
            review_due - review date has arrived
            expiring   - expires within 30 days
            healthy    - valid and more than 30 days from expiry
            no_expiry  - no expiry date has been recorded
        """
        today = timezone.localdate()

        if self.status != self.Status.ACTIVE:
            return "inactive"

        if self.expiry_date and self.expiry_date < today:
            return "expired"

        if self.review_date and self.review_date <= today:
            return "review_due"

        if self.expiry_date:
            if self.expiry_date <= today + timezone.timedelta(days=30):
                return "expiring"

            return "healthy"

        return "no_expiry"

    @property
    def health_status_label(self):
        """
        Human-readable label for the document health state.
        """
        labels = {
            "inactive": "Inactive",
            "expired": "Expired",
            "review_due": "Review due",
            "expiring": "Expiring soon",
            "healthy": "Healthy",
            "no_expiry": "No expiry",
        }

        return labels.get(
            self.health_status,
            "Unknown",
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



# ============================================================
# BULK DOCUMENT INTELLIGENCE IMPORT
# ============================================================

class BulkImportBatch(models.Model):
    """
    Represents one bulk document import session.

    Files are analysed first and are NOT immediately converted
    into permanent CompanyDocument records.

    The administrator reviews the proposed classifications and
    then confirms the import.
    """

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        ANALYSING = "analysing", "Analysing"
        REVIEW = "review", "Review Required"
        IMPORTING = "importing", "Importing"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partially Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    batch_reference = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
        db_index=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_document_import_batches",
    )

    total_files = models.PositiveIntegerField(default=0)

    processed_files = models.PositiveIntegerField(default=0)

    approved_files = models.PositiveIntegerField(default=0)

    imported_files = models.PositiveIntegerField(default=0)

    review_required = models.PositiveIntegerField(default=0)

    duplicate_count = models.PositiveIntegerField(default=0)

    failed_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bulk document import"
        verbose_name_plural = "Bulk document imports"

    def __str__(self):
        return self.batch_reference

    @property
    def progress_percentage(self):
        if not self.total_files:
            return 0

        return min(
            100,
            round(
                (self.processed_files / self.total_files) * 100
            ),
        )

    @property
    def pending_review_count(self):
        return self.items.filter(
            status=BulkImportItem.Status.REVIEW
        ).count()


class BulkImportItem(models.Model):
    """
    Individual file inside a BulkImportBatch.

    This stores the system's analysis BEFORE the final
    CompanyDocument record is created.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ANALYSING = "analysing", "Analysing"
        READY = "ready", "Ready"
        REVIEW = "review", "Review Required"
        APPROVED = "approved", "Approved"
        IMPORTED = "imported", "Imported"
        DUPLICATE = "duplicate", "Duplicate"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    batch = models.ForeignKey(
        BulkImportBatch,
        on_delete=models.CASCADE,
        related_name="items",
    )

    staging_file = models.FileField(
        storage=CompanyDocumentStorage(),
        upload_to="company_document_staging/%Y/%m/",
        max_length=500,
        blank=True,
        null=True,
    )

    original_filename = models.CharField(
        max_length=500,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    mime_type = models.CharField(
        max_length=255,
        blank=True,
    )

    file_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # --------------------------------------------------------
    # Extracted content
    # --------------------------------------------------------

    extracted_text = models.TextField(
        blank=True,
    )

    extraction_method = models.CharField(
        max_length=50,
        blank=True,
    )

    extraction_error = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    suggested_name = models.CharField(
        max_length=255,
        blank=True,
    )

    suggested_category = models.CharField(
        max_length=50,
        blank=True,
    )

    suggested_document_type = models.CharField(
        max_length=255,
        blank=True,
    )

    suggested_description = models.TextField(
        blank=True,
    )

    suggested_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    suggested_version = models.CharField(
        max_length=50,
        blank=True,
    )

    suggested_related_type = models.CharField(
        max_length=50,
        blank=True,
    )

    suggested_employee_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    suggested_customer_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    suggested_vehicle_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    suggested_supplier_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    suggested_contract_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    suggested_issue_date = models.DateField(
        null=True,
        blank=True,
    )

    suggested_expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    suggested_review_date = models.DateField(
        null=True,
        blank=True,
    )

    suggested_sensitive = models.BooleanField(
        default=False,
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence_score = models.PositiveSmallIntegerField(
        default=0,
    )

    confidence_label = models.CharField(
        max_length=30,
        blank=True,
    )

    classification_reasons = models.JSONField(
        default=list,
        blank=True,
    )

    extracted_fields = models.JSONField(
        default=dict,
        blank=True,
    )

    # --------------------------------------------------------
    # Duplicate detection
    # --------------------------------------------------------

    duplicate_document = models.ForeignKey(
        "CompanyDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulk_duplicate_candidates",
    )

    duplicate_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # Final imported document
    # --------------------------------------------------------

    imported_document = models.ForeignKey(
        "CompanyDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulk_import_source_items",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_company_document_import_items",
    )

    reviewer_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    analysed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    imported_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(
                fields=["batch", "status"]
            ),
            models.Index(
                fields=["file_hash"]
            ),
            models.Index(
                fields=["confidence_score"]
            ),
        ]

    def __str__(self):
        return self.original_filename

    @property
    def confidence_percent(self):
        return f"{self.confidence_score}%"

    @property
    def needs_review(self):
        return (
            self.status == self.Status.REVIEW
            or self.confidence_score < 85
        )


# ============================================================
# COMPLIANCE REQUIREMENTS
# ============================================================


class ComplianceRequirement(models.Model):
    """
    Defines a document that an entity is expected to have.

    This model intentionally does not replace Employee, Customer,
    Vehicle, Supplier or Contract models.

    It only defines the compliance requirement and allows the
    compliance service to determine whether the requirement is
    satisfied by an existing CompanyDocument.
    """

    class Scope(models.TextChoices):
        COMPANY = "company", "Company"
        EMPLOYEE = "employee", "Employee"
        CUSTOMER = "customer", "Customer"
        VEHICLE = "vehicle", "Vehicle"
        SUPPLIER = "supplier", "Supplier"
        CONTRACT = "contract", "Contract"

    name = models.CharField(
        max_length=180,
    )

    scope = models.CharField(
        max_length=30,
        choices=Scope.choices,
    )

    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text=(
            "CompanyDocument category used when matching "
            "existing documents."
        ),
    )

    document_type = models.CharField(
        max_length=180,
        blank=True,
        default="",
        help_text=(
            "CompanyDocument document type used for matching."
        ),
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    required = models.BooleanField(
        default=True,
    )

    active = models.BooleanField(
        default=True,
    )

    sensitive = models.BooleanField(
        default=False,
    )

    sort_order = models.PositiveIntegerField(
        default=100,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "scope",
            "sort_order",
            "name",
        ]
        indexes = [
            models.Index(
                fields=[
                    "scope",
                    "active",
                ]
            ),
            models.Index(
                fields=[
                    "category",
                    "document_type",
                ]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "scope",
                    "name",
                ],
                name="unique_compliance_requirement_scope_name",
            ),
        ]

    def __str__(self):
        return f"{self.get_scope_display()} — {self.name}"
