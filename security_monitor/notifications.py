
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import SecurityFinding

logger = logging.getLogger(__name__)

ALERT_TEMPLATE = "emails/security_monitor/security_alert.html"
REPORT_TEMPLATE = "emails/security_monitor/security_report.html"


def _email_configuration():
    """Return the configured security email recipient and dashboard URL."""
    recipient = getattr(settings, "SECURITY_ALERT_EMAIL", "")
    sender = getattr(settings, "DEFAULT_FROM_EMAIL", "")

    site_url = (
        getattr(settings, "SITE_URL", "")
        or "https://www.ydcleaning.com.au"
    )
    dashboard_url = (
        getattr(settings, "SECURITY_DASHBOARD_URL", "")
        or f"{site_url.rstrip('/')}/dashboard/security/"
    )

    if not recipient:
        logger.error("SECURITY_ALERT_EMAIL is not configured.")
        return None

    if not sender:
        logger.error("DEFAULT_FROM_EMAIL is not configured.")
        return None

    return recipient, sender, dashboard_url


def _send_html_email(*, subject, text_body, html_template, context):
    """Send a branded HTML email with a plain-text alternative."""
    configuration = _email_configuration()
    if configuration is None:
        return False

    recipient, sender, _dashboard_url = configuration

    try:
        html_body = render_to_string(html_template, context)

        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=sender,
            to=[recipient],
        )
        message.attach_alternative(html_body, "text/html")

        # Let failures reach the queue processor so it can retry.
        return message.send(fail_silently=False) == 1

    except Exception:
        logger.exception("Security email delivery failed.")
        return False


def send_security_alert(finding):
    """Send an individual security finding notification."""
    configuration = _email_configuration()
    if configuration is None:
        return False

    _recipient, _sender, dashboard_url = configuration

    subject = (
        f"[YD Security] [{finding.severity.upper()}] "
        f"{finding.title}"
    )

    text_body = f"""YD COMMERCIAL CLEANING SERVICES
SECURITY INCIDENT ALERT

Finding: {finding.title}
Severity: {finding.severity.upper()}
Status: {finding.get_status_display()}
Source: {finding.get_source_display()}
Path: {finding.path or "Not applicable"}
Source IP: {finding.source_ip or "Not recorded"}
First detected: {timezone.localtime(finding.first_seen)}
Last detected: {timezone.localtime(finding.last_seen)}
Occurrences: {finding.occurrences}

Description:
{finding.description}

Recommended action:
Review the finding in the authenticated security dashboard:
{dashboard_url}

This alert records a detected signal. It does not by itself
prove that a successful compromise occurred.
"""

    return _send_html_email(
        subject=subject,
        text_body=text_body.strip(),
        html_template=ALERT_TEMPLATE,
        context={
            "finding": finding,
            "dashboard_url": dashboard_url,
        },
    )


def send_security_report():
    """Send the scheduled security audit summary."""
    configuration = _email_configuration()
    if configuration is None:
        return False

    _recipient, _sender, dashboard_url = configuration

    findings = list(
        SecurityFinding.objects.exclude(
            status=SecurityFinding.Status.IGNORED
        ).order_by("-last_seen")[:100]
    )

    total_open = SecurityFinding.objects.filter(
        status=SecurityFinding.Status.OPEN
    ).count()

    investigating = SecurityFinding.objects.filter(
        status=SecurityFinding.Status.INVESTIGATING
    ).count()

    unresolved_statuses = [
        SecurityFinding.Status.OPEN,
        SecurityFinding.Status.INVESTIGATING,
    ]

    critical = SecurityFinding.objects.filter(
        severity=SecurityFinding.Severity.CRITICAL,
        status__in=unresolved_statuses,
    ).count()

    high = SecurityFinding.objects.filter(
        severity=SecurityFinding.Severity.HIGH,
        status__in=unresolved_statuses,
    ).count()

    generated_at = timezone.localtime()

    context = {
        "findings": findings,
        "total_open": total_open,
        "investigating": investigating,
        "critical": critical,
        "high": high,
        "generated_at": generated_at,
        "dashboard_url": dashboard_url,
    }

    lines = [
        "YD COMMERCIAL CLEANING SERVICES",
        "SCHEDULED SECURITY AUDIT REPORT",
        f"Generated: {generated_at:%d %b %Y, %H:%M %Z}",
        "",
        f"Open findings: {total_open}",
        f"Under investigation: {investigating}",
        f"Unresolved critical findings: {critical}",
        f"Unresolved high-severity findings: {high}",
        "",
        "RECENT FINDINGS",
    ]

    if findings:
        for finding in findings:
            lines.append(
                f"- [{finding.severity.upper()}] "
                f"[{finding.get_status_display()}] "
                f"{finding.title} | "
                f"{finding.get_source_display()} | "
                f"Last seen: "
                f"{timezone.localtime(finding.last_seen):%d %b %Y, %H:%M}"
            )
    else:
        lines.append("No non-ignored findings are currently recorded.")

    lines.extend([
        "",
        "Review and validate findings in the authenticated dashboard:",
        dashboard_url,
        "",
        "Scope: This report reflects findings recorded by the monitoring "
        "system. It is not a certification or a guarantee that all risks "
        "or security incidents have been detected.",
    ])

    return _send_html_email(
        subject="[YD Security] Scheduled Security Audit Report | YDCCS",
        text_body="\n".join(lines),
        html_template=REPORT_TEMPLATE,
        context=context,
    )
