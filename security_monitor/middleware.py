
import hashlib
import ipaddress
import logging
import re
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache

from .models import SecurityFinding

logger = logging.getLogger(__name__)

SUSPICIOUS_PATTERNS = [
    (
        re.compile(r"(\.\./|%2e%2e%2f)", re.IGNORECASE),
        "Possible path traversal attempt",
        SecurityFinding.Severity.HIGH,
    ),
    (
        re.compile(r"(<script\b|javascript:)", re.IGNORECASE),
        "Possible cross-site scripting probe",
        SecurityFinding.Severity.MEDIUM,
    ),
    (
        re.compile(
            r"(\bunion\s+select\b|\bor\s+1\s*=\s*1\b)",
            re.IGNORECASE,
        ),
        "Possible SQL injection probe",
        SecurityFinding.Severity.HIGH,
    ),
    (
        re.compile(
            r"(/\.env|/wp-admin|phpmyadmin|/etc/passwd)",
            re.IGNORECASE,
        ),
        "Possible sensitive-file or admin scan",
        SecurityFinding.Severity.HIGH,
    ),
    (
        re.compile(
            r"(information_schema|sleep\s*\()",
            re.IGNORECASE,
        ),
        "Possible database probing attempt",
        SecurityFinding.Severity.HIGH,
    ),
]

MAX_SCAN_LENGTH = 4096


class SecurityMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(
            settings, "SECURITY_MONITORING_ENABLED", True
        ):
            return self.get_response(request)

        # Inspect a bounded URL without storing query values or bodies.
        target = unquote(
            f"{request.path}?{request.META.get('QUERY_STRING', '')}"
        )[:MAX_SCAN_LENGTH]

        raw_ip = request.META.get("REMOTE_ADDR", "").strip()

        try:
            source_ip = str(ipaddress.ip_address(raw_ip))
        except ValueError:
            source_ip = None

        for pattern, title, severity in SUSPICIOUS_PATTERNS:
            if not pattern.search(target):
                continue

            try:
                from .scanners import record_finding

                fingerprint = hashlib.sha256(
                    f"{source_ip}:{title}:{request.path}".encode("utf-8")
                ).hexdigest()

                should_record = cache.add(
                    f"security_monitor:request:{fingerprint}",
                    1,
                    timeout=60,
                )

                if should_record:
                    record_finding(
                        title=title,
                        description=(
                            "A request matched a suspicious URL pattern. "
                            "This is a detection signal, not proof of a "
                            "successful attack."
                        ),
                        severity=severity,
                        source=SecurityFinding.Source.REQUEST,
                        path=request.path[:500],
                        source_ip=source_ip,
                        details={"method": request.method},
                    )

            except Exception:
                logger.exception(
                    "Unable to persist a security finding."
                )

            break

        return self.get_response(request)
