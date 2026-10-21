
from django.conf import settings
from django.db import models
from django.utils import timezone


class SecurityFinding(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFO = "info", "Informational"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    class Source(models.TextChoices):
        REQUEST = "request", "Request monitoring"
        AUDIT = "audit", "Scheduled audit"
        DJANGO = "django", "Django security check"
        DEPENDENCY = "dependency", "Dependency scan"
        UPTIME = "uptime", "Availability monitoring"

    fingerprint = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=220)
    description = models.TextField()
    severity = models.CharField(
        max_length=12,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.AUDIT,
    )
    path = models.CharField(max_length=500, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    occurrences = models.PositiveIntegerField(default=1)
    details = models.JSONField(default=dict, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_security_findings",
    )

    class Meta:
        ordering = ["-last_seen"]
        indexes = [
            models.Index(
                fields=["status", "severity"],
                name="secmon_status_sev_idx",
            ),
            models.Index(
                fields=["source", "-last_seen"],
                name="secmon_source_last_idx",
            ),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"



class SecurityAlertDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    finding = models.ForeignKey(
        SecurityFinding,
        on_delete=models.CASCADE,
        related_name="alert_deliveries",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"]),
        ]

    def __str__(self):
        return f"Alert for finding {self.finding_id}: {self.status}"
