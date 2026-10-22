
import logging
import io
import re
from contextlib import redirect_stderr, redirect_stdout

import requests
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from .models import SecurityFinding
from .scanners import record_finding


logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "Strict-Transport-Security": (
        SecurityFinding.Severity.HIGH,
        "HTTPS strict transport security header is missing",
    ),
    "X-Content-Type-Options": (
        SecurityFinding.Severity.MEDIUM,
        "Content type protection header is missing",
    ),
    "Content-Security-Policy": (
        SecurityFinding.Severity.MEDIUM,
        "Content Security Policy header is missing",
    ),
    "Referrer-Policy": (
        SecurityFinding.Severity.LOW,
        "Referrer policy header is missing",
    ),
}





def resolve_availability_findings():
    """Resolve active website availability findings after recovery."""
    SecurityFinding.objects.filter(
        title="Website availability check failed",
        source=SecurityFinding.Source.UPTIME,
        status__in=[
            SecurityFinding.Status.OPEN,
            SecurityFinding.Status.INVESTIGATING,
        ],
    ).update(
        status=SecurityFinding.Status.RESOLVED,
        resolved_at=timezone.now(),
        resolved_by=None,
    )



def resolve_header_finding(title):
    """Resolve an active missing-header finding after verification."""
    now = timezone.now()

    SecurityFinding.objects.filter(
        title=title,
        source=SecurityFinding.Source.AUDIT,
        path="/",
        status__in=[
            SecurityFinding.Status.OPEN,
            SecurityFinding.Status.INVESTIGATING,
        ],
    ).update(
        status=SecurityFinding.Status.RESOLVED,
        resolved_at=now,
        resolved_by=None,
    )


def audit_public_website():
    """Perform safe, read-only checks against the configured site."""
    site_url = getattr(settings, "SITE_URL", "").strip()

    if not site_url.startswith("https://"):
        record_finding(
            title="Production site URL is not HTTPS",
            description=(
                "Configure SITE_URL as the canonical HTTPS URL before "
                "running the production security audit."
            ),
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
        )
        return

    try:
        response = requests.get(
            site_url,
            timeout=(5, 20),
            allow_redirects=True,
            headers={"User-Agent": "YDCCS-Security-Monitor/1.0"},
        )
    except requests.RequestException as exc:
        record_finding(
            title="Website availability check failed",
            description=(
                "The configured website did not respond successfully "
                "to the monitoring request."
            ),
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.UPTIME,
            details={"error_type": type(exc).__name__},
        )
        return

    if response.status_code >= 500:
        record_finding(
            title="Website returned a server error",
            description=(
                f"The public website returned HTTP "
                f"{response.status_code} during the audit."
            ),
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.UPTIME,
            details={"status_code": response.status_code},
        )

    elif 200 <= response.status_code < 400:
        resolve_availability_findings()

    if response.url.startswith("http://"):
        record_finding(
            title="Website ended on an insecure HTTP URL",
            description=(
                "The final URL after redirects uses HTTP instead of HTTPS."
            ),
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
        )

    for header, (severity, title) in SECURITY_HEADERS.items():
        if header in response.headers:
            resolve_header_finding(title)
            continue

        # A report-only CSP header is active monitoring, not enforcement.
        if (
            header == "Content-Security-Policy"
            and "Content-Security-Policy-Report-Only" in response.headers
        ):
            resolve_header_finding(title)

            record_finding(
                title="Content Security Policy is report-only",
                description=(
                    "The public website sends a "
                    "Content-Security-Policy-Report-Only header. "
                    "This allows policy violations to be reported but "
                    "does not enforce the policy against browser resources."
                ),
                severity=SecurityFinding.Severity.INFO,
                source=SecurityFinding.Source.AUDIT,
                path="/",
                details={
                    "header": "Content-Security-Policy-Report-Only",
                    "enforced": False,
                },
            )
            continue

        record_finding(
            title=title,
            description=(
                f"The final response from {response.url} did not contain "
                f"the {header} header."
            ),
            severity=severity,
            source=SecurityFinding.Source.AUDIT,
            path="/",
            details={
                "missing_header": header,
                "checked_url": response.url,
                "status_code": response.status_code,
            },
        )

    # If CSP enforcement is present, the report-only finding is obsolete.
    if "Content-Security-Policy" in response.headers:
        resolve_header_finding(
            "Content Security Policy is report-only"
        )

    response.close()


def audit_django_configuration():
    """Capture Django's deployment check output for review."""
    output = io.StringIO()

    try:
        with redirect_stdout(output), redirect_stderr(output):
            call_command("check", "--deploy", verbosity=1)
    except Exception:
        logger.exception("Django deployment security check failed.")
        record_finding(
            title="Django deployment security check could not complete",
            description="Review the worker logs to diagnose the failed check.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.DJANGO,
        )
        return

    text = output.getvalue()

    # Match Django check IDs, e.g. security.W001.
    check_ids = sorted(set(re.findall(r"\bsecurity\.W\d+\b", text)))

    for check_id in check_ids:
        record_finding(
            title=f"Django deployment warning: {check_id}",
            description=(
                f"Django reported {check_id} during its deployment "
                "security check. Review the full diagnostic and remediate "
                "the underlying configuration issue."
            ),
            severity=SecurityFinding.Severity.MEDIUM,
            source=SecurityFinding.Source.DJANGO,
            details={"check_id": check_id},
        )
