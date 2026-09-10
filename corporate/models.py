from django.conf import settings
from django.db import models


class CorporateLead(models.Model):
    """
    Stores enquiries generated from the corporate section of the website.
    """

    LEAD_TYPE_CHOICES = [
        ("proposal", "Corporate Proposal"),
        ("team_contact", "Speak With Our Team"),
        ("multi_site", "Multi-Site Cleaning"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("qualified", "Qualified"),
        ("proposal_sent", "Proposal Sent"),
        ("negotiating", "Negotiating"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("on_hold", "On Hold"),
    ]

    INDUSTRY_CHOICES = [
        ("corporate_office", "Corporate Office"),
        ("property_management", "Property Management"),
        ("retail", "Retail"),
        ("healthcare", "Healthcare"),
        ("education", "Education"),
        ("hospitality", "Hospitality"),
        ("industrial", "Industrial"),
        ("construction", "Construction"),
        ("government", "Government"),
        ("warehouse", "Warehouse / Logistics"),
        ("other", "Other"),
    ]

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("multiple_weekly", "Multiple times per week"),
        ("weekly", "Weekly"),
        ("fortnightly", "Fortnightly"),
        ("monthly", "Monthly"),
        ("one_off", "One-off"),
        ("custom", "Custom / Flexible"),
    ]

    lead_type = models.CharField(
        max_length=30,
        choices=LEAD_TYPE_CHOICES,
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="new",
        db_index=True,
    )

    # Contact information
    full_name = models.CharField(max_length=200)

    job_title = models.CharField(
        max_length=150,
        blank=True,
    )

    company_name = models.CharField(
        max_length=200,
        blank=True,
    )

    email = models.EmailField()

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    # Business information
    industry = models.CharField(
        max_length=50,
        choices=INDUSTRY_CHOICES,
        blank=True,
    )

    number_of_sites = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    service_locations = models.TextField(
        blank=True,
        help_text="Suburbs, cities or locations requiring service.",
    )

    facility_size = models.CharField(
        max_length=150,
        blank=True,
        help_text="Approximate building/facility size.",
    )

    services_required = models.TextField(
        blank=True,
        help_text="Cleaning services requested by the customer.",
    )

    frequency = models.CharField(
        max_length=40,
        choices=FREQUENCY_CHOICES,
        blank=True,
    )

    preferred_start_date = models.DateField(
        null=True,
        blank=True,
    )

    current_cleaning_provider = models.CharField(
        max_length=200,
        blank=True,
    )

    # Multi-site requirements
    location_coverage = models.TextField(
        blank=True,
        help_text="Details about locations and geographic coverage.",
    )

    centralised_invoicing = models.BooleanField(
        default=False,
    )

    reporting_requirements = models.TextField(
        blank=True,
    )

    access_requirements = models.TextField(
        blank=True,
    )

    # Customer message
    message = models.TextField(
        blank=True,
    )

    # Lead attribution
    lead_source = models.CharField(
        max_length=100,
        default="corporate_page",
        blank=True,
    )

    landing_page = models.URLField(
        max_length=500,
        blank=True,
    )

    referrer = models.URLField(
        max_length=500,
        blank=True,
    )

    # Staff management
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_corporate_leads",
    )

    internal_notes = models.TextField(
        blank=True,
    )

    follow_up_date = models.DateField(
        null=True,
        blank=True,
    )

    # Consent
    consent = models.BooleanField(
        default=False,
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Corporate Lead"
        verbose_name_plural = "Corporate Leads"

    def __str__(self):
        company = self.company_name or "Individual"
        return f"{company} — {self.full_name}"

    @property
    def lead_type_display_name(self):
        return dict(self.LEAD_TYPE_CHOICES).get(
            self.lead_type,
            self.lead_type,
        )

    @property
    def status_display_name(self):
        return dict(self.STATUS_CHOICES).get(
            self.status,
            self.status,
        )

    @property
    def is_open(self):
        return self.status not in {"won", "lost"}