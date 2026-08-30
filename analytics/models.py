from django.db import models
import uuid


class Visitor(models.Model):
    """
    Anonymous website visitor.

    A Visitor represents a browser/device identity rather than
    a registered customer.
    """

    visitor_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    total_sessions = models.PositiveIntegerField(default=0)
    total_page_views = models.PositiveIntegerField(default=0)

    is_returning = models.BooleanField(default=False)

    # Non-sensitive technical information
    device_type = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    browser = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    def __str__(self):
        return f"Visitor {self.visitor_id}"


class VisitorSession(models.Model):
    """
    Represents one visit/session from a visitor.
    """

    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    landing_page = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    exit_page = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    referrer = models.URLField(
        max_length=1000,
        blank=True,
        default="",
    )

    # Traffic/campaign information
    utm_source = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    utm_medium = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    utm_campaign = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.session_id}"


class ActivityEvent(models.Model):
    """
    Individual activity performed by a visitor.
    """

    EVENT_TYPES = [
        ("PAGE_VIEW", "Page View"),
        ("CLICK", "Click"),
        ("SEARCH", "Search"),
        ("FORM_START", "Form Start"),
        ("FORM_SUBMIT", "Form Submit"),
        ("PHONE_CLICK", "Phone Click"),
        ("EMAIL_CLICK", "Email Click"),
        ("QUOTE_START", "Quote Start"),
        ("QUOTE_SUBMIT", "Quote Submit"),
        ("BOOKING_START", "Booking Start"),
        ("BOOKING_COMPLETE", "Booking Complete"),
        ("FAQ_OPEN", "FAQ Open"),
        ("DOWNLOAD", "Download"),
        ("VIDEO_PLAY", "Video Play"),
        ("GALLERY_VIEW", "Gallery View"),
        ("CTA_CLICK", "CTA Click"),
        ("SCROLL_DEPTH", "Scroll Depth"),
        ("TIME_ON_PAGE", "Time on Page"),
        ("PAGE_ENGAGEMENT", "Page Engagement"),
    ]

    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    session = models.ForeignKey(
        VisitorSession,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        db_index=True,
    )

    page_url = models.CharField(
        max_length=1000,
        blank=True,
        default="",
    )

    element = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class SearchEvent(models.Model):
    """
    Records searches made through the website.
    """

    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.CASCADE,
        related_name="searches",
    )

    session = models.ForeignKey(
        VisitorSession,
        on_delete=models.CASCADE,
        related_name="searches",
    )

    query = models.CharField(
        max_length=500,
        db_index=True,
    )

    page_url = models.CharField(
        max_length=1000,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    def __str__(self):
        return self.query