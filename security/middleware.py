import json

from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.core.validators import validate_email
from urllib.parse import unquote

from .services import (
    identifier_digest,
    limit_cache_counter,
    login_lock_state,
    record_security_event,
)


class SecurityAccessMiddleware(MiddlewareMixin):
    """Apply account blocks to already-authenticated sessions as well."""

    def process_request(self, request):
        user = request.user
        if not user.is_authenticated:
            return None

        blocked = not user.is_active
        identifier = user.get_username()
        if not blocked:
            _, lock_state = login_lock_state(identifier)
            blocked = lock_state is not None

        if not blocked:
            return None

        logout(request)
        if request.path.startswith("/dashboard/"):
            return redirect("dashboard_login")
        if request.path.startswith("/employee/"):
            return redirect("employee_login")
        if request.path.startswith("/portal/"):
            return redirect("portal_login")
        return None


class AttackMonitoringMiddleware(MiddlewareMixin):
    """Record high-signal scanning and injection patterns without body data."""

    SUSPICIOUS_MARKERS = (
        ("/wp-admin", "wordpress admin scan"),
        ("/.env", "environment file probe"),
        ("phpmyadmin", "database admin scan"),
        ("../", "path traversal probe"),
        ("%2e%2e", "encoded path traversal probe"),
        ("union select", "SQL injection pattern"),
        ("information_schema", "database schema probe"),
        ("sleep(", "SQL timing probe"),
        ("<script", "script injection pattern"),
        ("/etc/passwd", "system file probe"),
    )

    def process_request(self, request):
        target = unquote(
            f"{request.path}?{request.META.get('QUERY_STRING', '')}"
        ).casefold()
        match = next(
            (
                description
                for marker, description in self.SUSPICIOUS_MARKERS
                if marker in target
            ),
            None,
        )
        if not match:
            return None

        from .services import request_ip

        ip = request_ip(request) or "unknown"
        dedupe_key = f"security:scan:{ip}:{identifier_digest(match)}"
        if limit_cache_counter(dedupe_key, 1, 600):
            record_security_event(
                "suspicious_request",
                f"Automated monitor detected a {match}.",
                request=request,
                severity="high",
            )
        return None


class PublicEmailVerificationMiddleware(MiddlewareMixin):
    """Require a one-time email code before public email forms are processed."""

    EXCLUDED_PREFIXES = (
        "/admin/",
        "/api/",
        "/dashboard/",
        "/employee/",
        "/security/",
        "/static/",
        "/media/",
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != "POST" or request.path.startswith(self.EXCLUDED_PREFIXES):
            return None
        if request.path.startswith("/portal/") and request.path != "/portal/profile/":
            return None

        # This applies to the public website forms that accept contact details.
        # It does not read or store form bodies or uploaded files.
        submitted_emails = [
            value.strip().casefold()
            for name, value in request.POST.items()
            if "email" in name.casefold() and value.strip()
        ]
        if request.content_type == "application/json":
            try:
                payload = json.loads(request.body or b"{}")
            except (TypeError, ValueError):
                payload = {}

            def collect_json_emails(value):
                if isinstance(value, dict):
                    for name, nested in value.items():
                        if "email" in str(name).casefold():
                            if isinstance(nested, str) and nested.strip():
                                submitted_emails.append(nested.strip().casefold())
                            elif isinstance(nested, list):
                                submitted_emails.extend(
                                    item.strip().casefold()
                                    for item in nested
                                    if isinstance(item, str) and item.strip()
                                )
                        else:
                            collect_json_emails(nested)
                elif isinstance(value, list):
                    for nested in value:
                        collect_json_emails(nested)

            collect_json_emails(payload)

        email_values = list(dict.fromkeys(submitted_emails))
        if (
            request.path == "/portal/profile/"
            and request.user.is_authenticated
            and request.user.email
        ):
            current_email = request.user.email.strip().casefold()
            email_values = [email for email in email_values if email != current_email]
        if not email_values:
            return None

        for email in email_values:
            try:
                validate_email(email)
            except ValidationError:
                return HttpResponseBadRequest("Enter a valid email address.")

        receipt = request.session.get("verified_public_email", {})
        available = {
            item.get("email_hash")
            for item in receipt.get("emails", [])
            if item.get("expires_at", 0) > timezone.now().timestamp()
        }
        required = {identifier_digest(email) for email in email_values}
        if required.issubset(available):
            remaining = [
                item
                for item in receipt.get("emails", [])
                if item.get("expires_at", 0) > timezone.now().timestamp()
                and item.get("email_hash") not in required
            ]
            if remaining:
                request.session["verified_public_email"] = {"emails": remaining}
            else:
                request.session.pop("verified_public_email", None)
            request._verified_public_emails = email_values
            return None

        if request.content_type == "application/json":
            return JsonResponse(
                {
                    "success": False,
                    "requires_email_verification": True,
                    "emails": email_values,
                    "message": "Verify each email address before submitting this form.",
                },
                status=403,
            )
        return render(
            request,
            "security/public_email_verification_required.html",
            {"email": email_values[0], "emails": email_values},
            status=403,
        )

