from django.conf import settings
from django.db import models


class UserEmailVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_email_verification",
    )
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    activate_account = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserAccessBlock(models.Model):
    """Persist an administrator block across email verification flows."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_access_block",
    )
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_blocks_created",
    )
    reason = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LoginAttemptState(models.Model):
    """Persistent lockout state keyed by a normalized login identifier."""

    identifier_hash = models.CharField(max_length=64, unique=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_at = models.DateTimeField()
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["locked_until"])]


class SecurityEvent(models.Model):
    EVENT_TYPES = [
        ("login_lockout", "Login lockout"),
        ("locked_login", "Attempt during lockout"),
        ("suspicious_request", "Suspicious request"),
        ("email_verification", "Email verification abuse"),
    ]
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    severity = models.CharField(
        max_length=12,
        choices=SEVERITY_CHOICES,
        default="medium",
    )
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    identifier_hash = models.CharField(max_length=64, blank=True)
    path = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=500)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at", "event_type"]),
            models.Index(fields=["created_at", "severity"]),
        ]
        permissions = [
            ("access_dashboard", "Can access the staff dashboard"),
            ("manage_users", "Can manage dashboard users"),
            ("manage_security_roles", "Can manage security roles"),
            ("view_security_center", "Can view the security center"),
        ]


class SecurityAuditReport(models.Model):
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    summary = models.JSONField(default=dict)
    checks = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

