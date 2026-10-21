
import hashlib
import json

from django.db import transaction
from django.utils import timezone

from .models import SecurityAlertDelivery, SecurityFinding


def record_finding(
    *,
    title,
    description,
    severity,
    source,
    path="",
    details=None,
):
    details = details or {}

    identity = {
        "title": title,
        "source": source,
        "path": path,
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()

    now = timezone.now()

    with transaction.atomic():
        finding, created = SecurityFinding.objects.get_or_create(
            fingerprint=fingerprint,
            defaults={
                "title": title,
                "description": description,
                "severity": severity,
                "source": source,
                "path": path[:500],
                "first_seen": now,
                "last_seen": now,
                "occurrences": 1,
                "details": details,
            },
        )

        should_alert = False

        if created:
            should_alert = severity in (
                SecurityFinding.Severity.CRITICAL,
                SecurityFinding.Severity.HIGH,
            )
        else:
            was_resolved = (
                finding.status == SecurityFinding.Status.RESOLVED
            )

            finding.last_seen = now
            finding.occurrences += 1
            finding.description = description
            finding.severity = severity
            finding.details = details

            update_fields = [
                "last_seen",
                "occurrences",
                "description",
                "severity",
                "details",
            ]

            if was_resolved:
                finding.status = SecurityFinding.Status.OPEN
                finding.resolved_at = None
                finding.resolved_by = None
                update_fields.extend([
                    "status",
                    "resolved_at",
                    "resolved_by",
                ])

                should_alert = severity in (
                    SecurityFinding.Severity.CRITICAL,
                    SecurityFinding.Severity.HIGH,
                )

            finding.save(update_fields=update_fields)

        if should_alert:
            SecurityAlertDelivery.objects.create(finding=finding)

    return finding, created
