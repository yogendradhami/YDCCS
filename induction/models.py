import calendar
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from employees.models import Employee
from .storage import EmployeeOnboardingDocumentStorage


def add_calendar_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class InductionProgramme(models.Model):
    name = models.CharField(
        max_length=160,
        default="YD Commercial Cleaning New Starter Induction",
    )

    version = models.PositiveIntegerField(default=1)

    description = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-active", "-version"]

    def __str__(self):
        return f"{self.name} v{self.version}"


class InductionModule(models.Model):

    CATEGORY_CHOICES = [
        ("welcome", "Welcome & Company"),
        ("whs", "WHS & Safety"),
        ("operations", "Cleaning Operations"),
        ("conduct", "Conduct & Privacy"),
        ("role", "Role Specific"),
    ]

    ROLE_CHOICES = [
        ("all", "All Employees"),
        ("cleaner", "Cleaner"),
        ("supervisor", "Supervisor"),
        ("manager", "Manager"),
    ]

    code = models.SlugField(
        max_length=80,
        unique=True,
    )

    title = models.CharField(
        max_length=180,
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="whs",
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="all",
    )

    summary = models.CharField(
        max_length=300,
        blank=True,
    )

    content = models.TextField()

    acknowledgement_text = models.CharField(
        max_length=300,
        default=(
            "I have read, understood and agree to follow "
            "this module."
        ),
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    sort_order = models.PositiveIntegerField(
        default=10,
    )

    mandatory = models.BooleanField(
        default=True,
    )

    active = models.BooleanField(
        default=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "sort_order",
            "id",
        ]

    def __str__(self):
        return self.title


class InductionModuleVersion(models.Model):
    module = models.ForeignKey(
        InductionModule,
        on_delete=models.PROTECT,
        related_name="training_versions",
    )
    version = models.PositiveIntegerField()
    content = models.JSONField(default=dict)
    acknowledgement_text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["module_id", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "version"],
                name="unique_induction_module_version",
            )
        ]

    def clean(self):
        super().clean()
        if not isinstance(self.content, dict):
            raise ValidationError({"content": "Training content must be an object."})
        if self.content.get("legacy_snapshot"):
            return

        questions = self.content.get("assessment", [])
        if not isinstance(questions, list) or not 5 <= len(questions) <= 8:
            raise ValidationError(
                {"content": "A published training version needs 5–8 questions."}
            )
        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                raise ValidationError(
                    {"content": f"Assessment question {index} must be an object."}
                )
            choices = question.get("choices", [])
            correct = question.get("correct")
            if (
                not question.get("question")
                or not question.get("explanation")
                or not isinstance(choices, list)
                or len(choices) < 2
                or not isinstance(correct, int)
                or not 0 <= correct < len(choices)
            ):
                raise ValidationError(
                    {
                        "content": (
                            f"Assessment question {index} needs a prompt, "
                            "at least two choices, a valid correct answer and "
                            "an explanation."
                        )
                    }
                )

    def __str__(self):
        return f"{self.module.title} v{self.version}"


class EmployeeInduction(models.Model):

    STATUS_CHOICES = [
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    EMPLOYMENT_CHOICES = [
        ("casual", "Casual"),
        ("part_time", "Part-time"),
        ("full_time", "Full-time"),
        ("contractor", "Contractor"),
    ]

    EXPIRY_CHOICES = [
        (6, "6 months"),
        (12, "12 months"),
    ]

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="induction",
    )

    programme = models.ForeignKey(
        InductionProgramme,
        on_delete=models.PROTECT,
        related_name="inductions",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="assigned",
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_CHOICES,
        default="casual",
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    supervisor_name = models.CharField(
        max_length=150,
        blank=True,
    )

    primary_work_location = models.CharField(
        max_length=255,
        blank=True,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expiry_months = models.PositiveSmallIntegerField(
        choices=EXPIRY_CHOICES,
        default=12,
    )

    expires_on = models.DateField(
        null=True,
        blank=True,
    )

    renewal_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    induction_duration_minutes = models.PositiveIntegerField(
        default=60,
    )

    declaration_name = models.CharField(
        max_length=150,
        blank=True,
    )

    declaration_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    declaration_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    declaration_user_agent = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    @property
    def is_expired(self):
        return bool(
            self.status == "completed"
            and self.expires_on
            and self.expires_on <= timezone.localdate()
        )

    def begin_renewal_if_expired(self):
        if not self.is_expired:
            return False
        self.status = "in_progress"
        self.renewal_started_at = timezone.now()
        self.save(update_fields=["status", "renewal_started_at"])
        return True

    def latest_module_completion(self, module, module_version=None):
        completions = self.completions.filter(module=module)
        if module_version is not None:
            completions = completions.filter(module_version=module_version)
        if self.renewal_started_at:
            completions = completions.filter(
                completed_at__gte=self.renewal_started_at,
            )
        return completions.order_by(
            "-module_version",
            "-attempt_number",
            "-completed_at",
        ).first()

    def required_modules(self):
        queryset = InductionModule.objects.filter(
            active=True,
            mandatory=True,
        )

        queryset = queryset.filter(
            models.Q(role="all")
            | models.Q(role=self.employee.role)
        )

        return queryset.order_by(
            "sort_order",
            "id",
        )

    def completion_count(self):
        return len(self.completed_module_ids())

    def required_count(self):
        return self.required_modules().count()

    def completed_module_ids(self):
        completed_ids = set()
        for module in self.required_modules():
            completion = self.latest_module_completion(
                module,
                module_version=module.version,
            )
            if completion and completion.review_status == "approved":
                completed_ids.add(module.pk)
        return completed_ids

    def retraining_module_ids(self):
        retraining_ids = set()
        for module in self.required_modules():
            latest = self.latest_module_completion(
                module,
                module_version=module.version,
            )
            if latest and latest.review_status == "redo_required":
                retraining_ids.add(module.pk)
            elif not latest and self.completions.filter(module=module).exists():
                retraining_ids.add(module.pk)
        return retraining_ids

    def is_complete(self):
        required_count = self.required_count()
        return (
            required_count > 0
            and self.completion_count() >= required_count
            and bool(
                self.declaration_name
                and self.declaration_at
            )
        )

    def mark_started(self):

        if self.status == "assigned":

            self.status = "in_progress"

            self.started_at = (
                self.started_at
                or timezone.now()
            )

            self.save(
                update_fields=[
                    "status",
                    "started_at",
                ]
            )

    def mark_completed(self, request=None):
        if not self.is_complete():
            return False

        was_completed = self.status == "completed"
        self.status = "completed"
        if not was_completed or not self.completed_at:
            self.completed_at = timezone.now()
            self.expires_on = add_calendar_months(
                timezone.localdate(self.completed_at),
                self.expiry_months,
            )
        self.renewal_started_at = None

        if not self.declaration_at:
            self.declaration_at = timezone.now()

        if request:

            self.declaration_ip = (
                request.META.get("REMOTE_ADDR")
            )

            self.declaration_user_agent = (
                request.META.get(
                    "HTTP_USER_AGENT",
                    "",
                )[:2000]
            )

        self.save()

        return True

    def __str__(self):

        return (
            f"{self.employee.full_name} — "
            f"{self.programme}"
        )


class InductionModuleCompletion(models.Model):

    REVIEW_STATUS_CHOICES = [
        ("pending", "Awaiting manager review"),
        ("approved", "Approved"),
        ("redo_required", "Redo required"),
    ]

    induction = models.ForeignKey(
        EmployeeInduction,
        on_delete=models.CASCADE,
        related_name="completions",
    )

    module = models.ForeignKey(
        InductionModule,
        on_delete=models.PROTECT,
        related_name="completions",
    )

    module_title_snapshot = models.CharField(
        max_length=180,
    )

    module_version = models.PositiveIntegerField(
        default=1,
    )

    attempt_number = models.PositiveSmallIntegerField(default=1)

    completed_at = models.DateTimeField(
        auto_now_add=True,
    )

    acknowledgement = models.BooleanField(
        default=True,
    )

    acknowledgement_text = models.CharField(
        max_length=300,
    )

    notes = models.TextField(
        blank=True,
    )

    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default="pending",
    )

    review_note = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_induction_completions",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "induction",
                    "module",
                    "module_version",
                    "attempt_number",
                ],
                name=(
                    "unique_induction_module_completion"
                ),
            )
        ]

        ordering = [
            "completed_at",
        ]

    def __str__(self):

        return (
            f"{self.induction.employee.full_name} — "
            f"{self.module_title_snapshot}"
        )


class InductionModuleReview(models.Model):
    completion = models.ForeignKey(
        InductionModuleCompletion,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    decision = models.CharField(
        max_length=20,
        choices=InductionModuleCompletion.REVIEW_STATUS_CHOICES,
    )
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="induction_module_reviews",
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reviewed_at", "-pk"]


class InductionAssessmentAttempt(models.Model):
    induction = models.ForeignKey(
        EmployeeInduction,
        on_delete=models.CASCADE,
        related_name="assessment_attempts",
    )
    module = models.ForeignKey(
        InductionModule,
        on_delete=models.PROTECT,
        related_name="assessment_attempts",
    )
    module_version = models.PositiveIntegerField()
    submission_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    answers = models.JSONField(default=dict)
    score = models.PositiveSmallIntegerField()
    passed = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at", "-pk"]
        indexes = [
            models.Index(
                fields=["induction", "module", "module_version", "-submitted_at"],
                name="ind_assessment_lookup_idx",
            )
        ]

    def __str__(self):
        return (
            f"{self.induction.employee.full_name} — "
            f"{self.module.title} v{self.module_version}: {self.score}%"
        )


class InductionSupervisorVerification(models.Model):
    RESULT_CHOICES = [
        ("competent", "Competent"),
        ("further_training", "Further training required"),
    ]

    induction = models.ForeignKey(
        EmployeeInduction,
        on_delete=models.CASCADE,
        related_name="supervisor_verifications",
    )
    module = models.ForeignKey(
        InductionModule,
        on_delete=models.PROTECT,
        related_name="supervisor_verifications",
    )
    module_version = models.PositiveIntegerField()
    practical_task = models.CharField(max_length=300)
    result = models.CharField(max_length=24, choices=RESULT_CHOICES)
    comments = models.TextField(blank=True)
    verified_at = models.DateTimeField(default=timezone.now)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="induction_verifications",
    )

    class Meta:
        ordering = ["-verified_at", "-pk"]

    def __str__(self):
        return (
            f"{self.induction.employee.full_name} — "
            f"{self.module.title}: {self.get_result_display()}"
        )


class InductionExpiryReminder(models.Model):
    PORTAL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("skipped", "Skipped"),
    ]
    EMAIL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("skipped", "Skipped"),
    ]

    induction = models.ForeignKey(
        EmployeeInduction,
        on_delete=models.CASCADE,
        related_name="expiry_reminders",
    )
    expiry_date = models.DateField()
    days_before_expiry = models.PositiveSmallIntegerField()
    portal_status = models.CharField(
        max_length=12,
        choices=PORTAL_STATUS_CHOICES,
        default="pending",
    )
    email_status = models.CharField(
        max_length=12,
        choices=EMAIL_STATUS_CHOICES,
        default="pending",
    )
    portal_sent_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["induction", "expiry_date", "days_before_expiry"],
                name="unique_induction_expiry_reminder",
            )
        ]


# ==========================================================
# EMPLOYEE ONBOARDING & COMPLIANCE
# ==========================================================

from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


def onboarding_document_upload_path(instance, filename):
    """
    Store onboarding documents in employee-specific directories
    with a generated filename.

    The original filename is stored separately for display.
    """

    extension = Path(filename).suffix.lower()

    return (
        f"private/onboarding/"
        f"employee_{instance.employee_id}/"
        f"{uuid.uuid4().hex}{extension}"
    )


class OnboardingRequirement(models.Model):

    CATEGORY_CHOICES = [
        ("identity", "Identity"),
        ("employment", "Employment"),
        ("right_to_work", "Right to Work"),
        ("compliance", "Compliance"),
        ("training", "Training"),
        ("licence", "Licence / Certificate"),
        ("policy", "Policy"),
        ("other", "Other"),
    ]

    ROLE_CHOICES = [
        ("all", "All Employees"),
        ("cleaner", "Cleaner"),
        ("supervisor", "Supervisor"),
        ("manager", "Manager"),
    ]

    code = models.SlugField(
        max_length=100,
        unique=True,
    )

    title = models.CharField(
        max_length=180,
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="employment",
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="all",
    )

    description = models.TextField(
        blank=True,
    )

    required = models.BooleanField(
        default=True,
    )

    employee_upload_allowed = models.BooleanField(
        default=True,
    )

    expiry_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Number of days until the document expires. "
            "Leave blank if it does not expire."
        ),
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    sort_order = models.PositiveIntegerField(
        default=10,
    )

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "sort_order",
            "id",
        ]

    def __str__(self):
        return self.title


class EmployeeOnboardingProfile(models.Model):

    STATUS_CHOICES = [
        ("pending_documents", "Documents Required"),
        ("under_review", "Under HR Review"),
        ("compliance_complete", "Compliance Complete"),
        ("ready", "Ready for Work"),
        ("blocked", "Blocked"),
    ]

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="onboarding",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending_documents",
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_onboarding_reviews",
    )

    ready_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "status",
            "-updated_at",
        ]

    def __str__(self):
        return (
            f"{self.employee.full_name} onboarding"
        )

    def required_requirements(self):
        return (
            OnboardingRequirement.objects
            .filter(
                active=True,
                required=True,
            )
            .filter(
                Q(role="all")
                | Q(role=self.employee.role)
            )
            .order_by(
                "sort_order",
                "id",
            )
        )

    def current_document_for(self, requirement):
        return (
            EmployeeOnboardingDocument.objects
            .filter(
                employee=self.employee,
                requirement=requirement,
                is_current=True,
            )
            .order_by("-version", "-uploaded_at")
            .first()
        )

    def missing_requirements(self):
        missing = []

        for requirement in self.required_requirements():
            document = self.current_document_for(
                requirement
            )

            if not document:
                missing.append(requirement)

        return missing

    def pending_documents(self):
        return (
            EmployeeOnboardingDocument.objects
            .filter(
                employee=self.employee,
                is_current=True,
                status="pending",
            )
            .select_related("requirement")
        )

    def rejected_documents(self):
        return (
            EmployeeOnboardingDocument.objects
            .filter(
                employee=self.employee,
                is_current=True,
                status="rejected",
            )
            .select_related("requirement")
        )

    def expired_documents(self):
        return (
            EmployeeOnboardingDocument.objects
            .filter(
                employee=self.employee,
                is_current=True,
                status="approved",
                expires_at__isnull=False,
                expires_at__lt=timezone.localdate(),
            )
            .select_related("requirement")
        )

    def approved_required_count(self):
        count = 0

        for requirement in self.required_requirements():

            document = self.current_document_for(
                requirement
            )

            if not document:
                continue

            if document.status != "approved":
                continue

            if (
                document.expires_at
                and document.expires_at < timezone.localdate()
            ):
                continue

            count += 1

        return count

    def required_count(self):
        return self.required_requirements().count()

    def completion_percentage(self):

        total = self.required_count()

        if total == 0:
            return 0

        completed = self.approved_required_count()

        return round(
            (completed / total) * 100
        )

    def induction_completed(self):

        return EmployeeInduction.objects.filter(
            employee=self.employee,
            status="completed",
        ).exists()

    def can_be_ready_for_work(self):

        if not self.induction_completed():
            return False

        if self.missing_requirements():
            return False

        if self.pending_documents().exists():
            return False

        if self.rejected_documents().exists():
            return False

        if self.expired_documents().exists():
            return False

        return True

    def refresh_status(self):
        """
        Refresh the compliance workflow status.

        Important:
        This method NEVER grants Ready for Work automatically.

        Ready for Work must be explicitly granted by an
        authorised HR/staff user through the HR workflow.
        """

        # A blocked employee remains blocked until HR explicitly
        # changes the status.
        if self.status == "blocked":
            return

        # Once the employee has satisfied all induction and
        # document requirements, they are compliance-complete.
        #
        # They are NOT yet Ready for Work.
        if self.can_be_ready_for_work():
            if self.status != "ready":
                self.status = "compliance_complete"

        elif (
            self.pending_documents().exists()
            or self.approved_required_count() > 0
        ):
            # Documents exist or are waiting for HR review.
            #
            # Do not downgrade an employee who has already been
            # explicitly approved unless their compliance becomes
            # invalid.
            self.status = "under_review"

        else:
            self.status = "pending_documents"

        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )



    def approve_for_work(self, user):
        """
        Explicit HR approval for work eligibility.

        This is intentionally separate from document compliance.
        """

        if not self.can_be_ready_for_work():
            raise ValueError(
                "Employee does not satisfy all onboarding "
                "requirements."
            )

        self.status = "ready"
        self.ready_at = timezone.now()

        self.reviewed_by = user
        self.reviewed_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "ready_at",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )


def block_from_work(self, user, notes=""):
    """
    Explicitly block an employee from work.
    """

    self.status = "blocked"

    self.reviewed_by = user
    self.reviewed_at = timezone.now()

    if notes:
        self.notes = notes

    self.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "notes",
            "updated_at",
        ]
    )


class EmployeeOnboardingDocument(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="onboarding_documents",
    )

    requirement = models.ForeignKey(
        OnboardingRequirement,
        on_delete=models.PROTECT,
        related_name="employee_documents",
    )

    file = models.FileField(
        storage=EmployeeOnboardingDocumentStorage(),
        upload_to=onboarding_document_upload_path,
    )

    original_filename = models.CharField(
        max_length=255,
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    is_current = models.BooleanField(
        default=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_document_reviews",
    )

    review_notes = models.TextField(
        blank=True,
    )

    expires_at = models.DateField(
        null=True,
        blank=True,
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    acknowledged_name = models.CharField(
        max_length=150,
        blank=True,
    )

    uploaded_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-is_current",
            "-uploaded_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "employee",
                    "requirement",
                    "version",
                ],
                name="unique_onboarding_document_version",
            ),
        ]

    def __str__(self):
        return (
            f"{self.employee.full_name} - "
            f"{self.requirement.title} "
            f"v{self.version}"
        )

    def calculate_expiry(self):

        if not self.requirement.expiry_days:
            return None

        return (
            timezone.localdate()
            + timedelta(
                days=self.requirement.expiry_days
            )
        )