
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import SecurityFinding

logger = logging.getLogger(__name__)


def send_security_alert(finding):
    recipient = getattr(settings, "SECURITY_ALERT_EMAIL", "")

    if not recipient:
        logger.warning("SECURITY_ALERT_EMAIL is not configured.")
        return False

    subject = (
        f"[YD Security] {finding.severity.upper()}: "
        f"{finding.title}"
    )

    body = f"""
YD Commercial Cleaning Services
Security incident notification

Title: {finding.title}
Severity: {finding.severity.upper()}
Status: {finding.status}
Source: {finding.source}
Path: {finding.path or "Not applicable"}
First detected: {finding.first_seen}
Last detected: {finding.last_seen}
Occurrences: {finding.occurrences}

Details:
{finding.description}

This alert indicates a detected signal and does not, by itself,
prove that a successful compromise occurred.

Please sign in to your dashboard and investigate the finding.
"""

    try:
        sent = send_mail(
            subject=subject,
            message=body.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return sent == 1
    except Exception:
        logger.exception("Failed to send security alert.")
        return False


def send_security_report():
    recipient = getattr(settings, "SECURITY_ALERT_EMAIL", "")
    if not recipient:
        logger.warning("SECURITY_ALERT_EMAIL is not configured.")
        return False

    findings = SecurityFinding.objects.exclude(
        status=SecurityFinding.Status.IGNORED
    ).order_by("-last_seen")[:100]

    total_open = SecurityFinding.objects.filter(
        status=SecurityFinding.Status.OPEN
    ).count()

    critical = SecurityFinding.objects.filter(
        severity=SecurityFinding.Severity.CRITICAL,
        status__in=[
            SecurityFinding.Status.OPEN,
            SecurityFinding.Status.INVESTIGATING,
        ],
    ).count()

    lines = [
        "YD Commercial Cleaning Services",
        "Scheduled security audit report",
        f"Generated: {timezone.localtime():%Y-%m-%d %H:%M}",
        "",
        f"Open findings: {total_open}",
        f"Unresolved critical findings: {critical}",
        "",
        "Recent findings:",
    ]

    for finding in findings:
        lines.append(
            f"- [{finding.severity.upper()}] "
            f"[{finding.status}] {finding.title} "
            f"(last seen {finding.last_seen})"
        )

    lines.extend([
        "",
        "Review findings in the authenticated security dashboard.",
        "This report covers recorded detections, not every possible attack.",
    ])

    try:
        return send_mail(
            subject="[YD Security] Scheduled audit report",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        ) == 1
    except Exception:
        logger.exception("Failed to send security report.")
        return False
