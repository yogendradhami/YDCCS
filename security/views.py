import hashlib
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.crypto import constant_time_compare, get_random_string
from django.views.decorators.http import require_POST

from dashboard.models import ActivityLog

from .forms import (
    ManagedUserCreateForm,
    ManagedUserUpdateForm,
    PositionForm,
    position_has_dashboard_access,
)
from .models import (
    LoginAttemptState,
    SecurityAuditReport,
    SecurityEvent,
    UserAccessBlock,
    UserEmailVerification,
)
from .services import (
    clear_user_login_lock,
    identifier_digest,
    limit_cache_counter,
    request_ip,
    record_security_event,
)

User = get_user_model()
EMAIL_CODE_SESSION_KEY = "security_public_email_code"
VERIFIED_EMAIL_SESSION_KEY = "verified_public_email"
EMAIL_CODE_LIFETIME = timedelta(minutes=10)
ACCOUNT_VERIFICATION_LIFETIME = timedelta(hours=24)


def _can_manage_users(user):
    return user.is_superuser or user.has_perm("security.manage_users")


def _can_view_security_center(user):
    return user.is_superuser or user.has_perm("security.view_security_center")


def _can_manage_roles(user):
    return user.is_superuser or user.has_perm("security.manage_security_roles")


def _is_protected_user(user):
    return user.is_superuser or user.groups.filter(
        Q(name="Administrator")
        | Q(
            permissions__content_type__app_label="security",
            permissions__codename="manage_security_roles",
        )
    ).exists()


def _user_needs_email_verification(user):
    if UserEmailVerification.objects.filter(user=user).exists():
        return True
    customer = getattr(user, "customer_profile", None)
    return bool(customer and not customer.email_verified)


def _forbidden(request):
    return HttpResponseForbidden("You do not have permission to manage security settings.")


def _request_data(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or b"{}")
        except (TypeError, ValueError):
            return {}
    return request.POST


@require_POST
def send_public_email_code(request):
    data = _request_data(request)
    email = str(data.get("email", "")).strip().casefold()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse(
            {"success": False, "message": "Enter a valid email address."},
            status=400,
        )

    email_hash = identifier_digest(email)
    ip = request_ip(request) or "unknown"
    if not limit_cache_counter(
        f"security:email-code:email:{email_hash}", 5, 3600
    ) or not limit_cache_counter(
        f"security:email-code:ip:{identifier_digest(ip)}", 12, 3600
    ):
        rate_event_key = f"security:email-rate-event:{identifier_digest(ip)}"
        if limit_cache_counter(rate_event_key, 1, 600):
            record_security_event(
                "email_verification",
                "Email verification code request rate limit was exceeded.",
                request=request,
                severity="medium",
                identifier_hash=email_hash,
            )
        return JsonResponse(
            {"success": False, "message": "Too many code requests. Try again later."},
            status=429,
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    request.session[EMAIL_CODE_SESSION_KEY] = {
        "email_hash": email_hash,
        "code_hash": make_password(code),
        "expires_at": (timezone.now() + EMAIL_CODE_LIFETIME).timestamp(),
        "attempts": 0,
    }

    try:
        sent = send_mail(
            "Verify your email for YD Commercial Cleaning",
            (
                f"Your one-time verification code is {code}.\n\n"
                "It expires in 10 minutes. If you did not request this code, "
                "you can ignore this email."
            ),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        record_security_event(
            "email_verification",
            "A public email verification message could not be sent.",
            request=request,
            severity="low",
            identifier_hash=email_hash,
        )
        return JsonResponse(
            {"success": False, "message": "We could not send a verification code."},
            status=503,
        )

    if sent != 1:
        return JsonResponse(
            {"success": False, "message": "We could not send a verification code."},
            status=503,
        )
    return JsonResponse(
        {"success": True, "message": "Verification code sent. Check your inbox."}
    )


@require_POST
def verify_public_email_code(request):
    data = _request_data(request)
    email = str(data.get("email", "")).strip().casefold()
    code = str(data.get("code", "")).strip()
    challenge = request.session.get(EMAIL_CODE_SESSION_KEY, {})

    challenge_valid = (
        challenge.get("email_hash") == identifier_digest(email)
        and challenge.get("expires_at", 0) > timezone.now().timestamp()
    )
    if not challenge_valid:
        request.session.pop(EMAIL_CODE_SESSION_KEY, None)
        return JsonResponse(
            {"success": False, "message": "Request a new verification code."},
            status=400,
        )

    attempts = int(challenge.get("attempts", 0))
    if attempts >= 5:
        request.session.pop(EMAIL_CODE_SESSION_KEY, None)
        return JsonResponse(
            {"success": False, "message": "Too many attempts. Request a new code."},
            status=429,
        )

    if not check_password(code, challenge.get("code_hash", "")):
        challenge["attempts"] = attempts + 1
        if challenge["attempts"] >= 5:
            request.session.pop(EMAIL_CODE_SESSION_KEY, None)
            record_security_event(
                "email_verification",
                "Five incorrect email verification codes were submitted.",
                request=request,
                severity="medium",
                identifier_hash=identifier_digest(email),
            )
        else:
            request.session[EMAIL_CODE_SESSION_KEY] = challenge
        return JsonResponse(
            {"success": False, "message": "That verification code is incorrect."},
            status=400,
        )

    request.session.pop(EMAIL_CODE_SESSION_KEY, None)
    receipt = request.session.get(VERIFIED_EMAIL_SESSION_KEY, {})
    verified_emails = [
        item
        for item in receipt.get("emails", [])
        if item.get("expires_at", 0) > timezone.now().timestamp()
        and item.get("email_hash") != identifier_digest(email)
    ]
    verified_emails.append(
        {
            "email_hash": identifier_digest(email),
            "expires_at": (timezone.now() + timedelta(minutes=20)).timestamp(),
        }
    )
    request.session[VERIFIED_EMAIL_SESSION_KEY] = {"emails": verified_emails[-10:]}
    request.session.cycle_key()
    return JsonResponse({"success": True, "message": "Email verified."})


def activate_managed_user(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id, is_active=False)
        verification = user.security_email_verification
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, UserEmailVerification.DoesNotExist):
        user = None
        verification = None

    if (
        user is None
        or verification is None
        or verification.expires_at <= timezone.now()
        or not constant_time_compare(
            verification.token_hash,
            hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )
        or not default_token_generator.check_token(user, token)
    ):
        messages.error(request, "This account verification link is invalid or expired.")
        return redirect("dashboard_login")

    if request.method != "POST":
        return render(request, "security/activate_user.html", {"user": user})

    explicitly_blocked = UserAccessBlock.objects.filter(user=user).exists()
    user.is_active = verification.activate_account and not explicitly_blocked
    user.save(update_fields=["is_active"])
    verification.delete()
    if user.is_active:
        messages.success(request, "Email verified. Your account is ready to use.")
    else:
        messages.success(request, "Email verified. The account remains blocked until an administrator activates it.")
    return redirect("dashboard_login")


def _send_user_activation_email(request, user, *, activate_account=True):
    token = default_token_generator.make_token(user)
    UserEmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "expires_at": timezone.now() + ACCOUNT_VERIFICATION_LIFETIME,
            "activate_account": activate_account,
        },
    )
    verification_url = request.build_absolute_uri(
        reverse(
            "security_activate_user",
            kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": token,
            },
        )
    )
    send_mail(
        "Verify your dashboard account",
        (
            f"Hello {user.first_name},\n\n"
            "An administrator created a dashboard account for you. "
            "Verify that you own this email address to activate the account:\n\n"
            f"{verification_url}\n\n"
            "This link expires in 24 hours."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def user_list(request):
    if not _can_manage_users(request.user):
        return _forbidden(request)

    users = User.objects.prefetch_related("groups").order_by("username")
    now = timezone.now()
    blocked_user_ids = set(
        UserAccessBlock.objects.values_list("user_id", flat=True)
    )
    lock_map = {
        row.identifier_hash: row
        for row in LoginAttemptState.objects.filter(
            locked_until__gt=now,
        )
    }
    user_rows = []
    for user in users:
        user_rows.append(
            {
                "user": user,
                "lock": lock_map.get(identifier_digest(user.get_username())),
                "pending_email_verification": _user_needs_email_verification(user),
                "admin_blocked": user.pk in blocked_user_ids,
            }
        )
    return render(
        request,
        "security/user_list.html",
        {
            "user_rows": user_rows,
            "can_manage_roles": _can_manage_roles(request.user),
        },
    )


def user_create(request):
    if not _can_manage_users(request.user):
        return _forbidden(request)

    if request.method == "POST":
        form = ManagedUserCreateForm(request.POST, user=request.user)
        if form.is_valid():
            position = form.cleaned_data["position"]
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=form.cleaned_data["email"],
                        email=form.cleaned_data["email"],
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                        password=form.cleaned_data["password1"],
                        is_active=False,
                        is_staff=position_has_dashboard_access(position),
                    )
                    user.groups.set([position])
            except (IntegrityError, ValidationError):
                form.add_error("email", "An account already uses this email address.")
            else:
                try:
                    _send_user_activation_email(request, user)
                except Exception:
                    user.delete()
                    messages.error(
                        request,
                        "We could not send the verification email, so the account was not created.",
                    )
                else:
                    messages.success(
                        request,
                        f"Account created for {user.email}. They must verify their email before signing in.",
                    )
                    return redirect("security_user_list")
    else:
        form = ManagedUserCreateForm(user=request.user)

    return render(request, "security/user_form.html", {"form": form, "is_create": True})


def user_edit(request, user_id):
    if not _can_manage_users(request.user):
        return _forbidden(request)
    user = get_object_or_404(User.objects.prefetch_related("groups"), pk=user_id)
    if _is_protected_user(user) and not request.user.is_superuser:
        return _forbidden(request)

    if request.method == "POST":
        form = ManagedUserUpdateForm(request.POST, user=request.user, instance=user)
        if form.is_valid():
            position = form.cleaned_data["position"]
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.groups.set([position])
            user.is_staff = position_has_dashboard_access(position)
            user.save(update_fields=["first_name", "last_name", "is_staff"])
            messages.success(request, f"Updated {user.email or user.username}.")
            return redirect("security_user_list")
    else:
        form = ManagedUserUpdateForm(user=request.user, instance=user)

    return render(
        request,
        "security/user_form.html",
        {"form": form, "is_create": False, "managed_user": user},
    )


@require_POST
def user_access_action(request, user_id, action):
    if not _can_manage_users(request.user):
        return _forbidden(request)
    user = get_object_or_404(User, pk=user_id)
    if _is_protected_user(user) and not request.user.is_superuser:
        return _forbidden(request)
    if user.pk == request.user.pk and action == "block":
        messages.error(request, "You cannot block your own account.")
        return redirect("security_user_list")

    pending_verification = _user_needs_email_verification(user)
    if action == "block":
        UserAccessBlock.objects.update_or_create(
            user=user,
            defaults={"blocked_by": request.user},
        )
        user.is_active = False
        user.save(update_fields=["is_active"])
        messages.success(request, f"Blocked {user.email or user.username}.")
    elif action == "unblock":
        if pending_verification:
            messages.error(
                request,
                "This account is waiting for email verification and cannot be unblocked yet.",
            )
            return redirect("security_user_list")
        employee = getattr(user, "employee_profile", None)
        if employee and not employee.active:
            messages.error(
                request,
                "This employee account cannot be unblocked while the employee record is inactive.",
            )
            return redirect("security_user_list")
        customer = getattr(user, "customer_profile", None)
        if customer and not customer.email_verified:
            messages.error(
                request,
                "This customer account cannot be unblocked until its email is verified.",
            )
            return redirect("security_user_list")
        UserAccessBlock.objects.filter(user=user).delete()
        user.is_active = True
        user.save(update_fields=["is_active"])
        clear_user_login_lock(user)
        messages.success(request, f"Unblocked {user.email or user.username}.")
    elif action == "clear-lock":
        clear_user_login_lock(user)
        messages.success(request, f"Cleared the temporary login lock for {user.email or user.username}.")
    elif action == "resend-verification":
        if not pending_verification:
            messages.info(request, "This user does not need email verification.")
            return redirect("security_user_list")
        try:
            if UserEmailVerification.objects.filter(user=user).exists():
                employee = getattr(user, "employee_profile", None)
                _send_user_activation_email(
                    request,
                    user,
                    activate_account=user.is_staff or employee is None or employee.active,
                )
            else:
                from portal.views import send_customer_verification_email

                send_customer_verification_email(request, user.customer_profile)
        except Exception:
            messages.error(request, "The verification email could not be sent.")
        else:
            messages.success(request, f"Verification email sent to {user.email}.")
    else:
        return _forbidden(request)

    try:
        ActivityLog.objects.create(
            user=request.user,
            action_type="settings",
            title="User Access Updated",
            description=f"{request.user.username} performed {action} for {user.username}.",
        )
    except Exception:
        pass
    return redirect("security_user_list")


def position_list(request):
    if not _can_manage_users(request.user):
        return _forbidden(request)
    return render(
        request,
        "security/position_list.html",
        {"positions": Group.objects.prefetch_related("permissions").order_by("name")},
    )


def position_edit(request, position_id=None):
    if not _can_manage_roles(request.user):
        return _forbidden(request)
    position = get_object_or_404(Group, pk=position_id) if position_id else None
    if position and not request.user.is_superuser and (
        position.name == "Administrator"
        or position.permissions.filter(
            content_type__app_label="security",
            codename="manage_security_roles",
        ).exists()
    ):
        return _forbidden(request)
    if request.method == "POST":
        form = PositionForm(request.POST, instance=position, user=request.user)
        if form.is_valid():
            group = form.save()
            for member in group.user_set.all():
                member.is_staff = member.groups.filter(
                    permissions__content_type__app_label="security",
                    permissions__codename="access_dashboard",
                ).exists()
                member.save(update_fields=["is_staff"])
            messages.success(request, f"Position {group.name} saved.")
            return redirect("security_position_list")
    else:
        form = PositionForm(instance=position, user=request.user)
    return render(
        request,
        "security/position_form.html",
        {"form": form, "position": position},
    )


def _security_checks():
    password_minimum = max(
        [
            validator.get("OPTIONS", {}).get("min_length", 0)
            for validator in settings.AUTH_PASSWORD_VALIDATORS
            if validator["NAME"].endswith("MinimumLengthValidator")
        ]
        or [0]
    )
    checks = [
        {
            "name": "Login lockout",
            "status": "pass",
            "detail": "Five failed attempts trigger a 30-minute account lock.",
        },
        {
            "name": "Password length",
            "status": "pass" if password_minimum >= 12 else "warning",
            "detail": f"Configured minimum length: {password_minimum} characters.",
        },
        {
            "name": "Production debug mode",
            "status": "fail" if settings.IS_PRODUCTION and settings.DEBUG else "pass",
            "detail": "Debug mode must be disabled in production.",
        },
        {
            "name": "HTTPS redirect",
            "status": "pass" if settings.SECURE_SSL_REDIRECT else "warning",
            "detail": "HTTP requests are redirected to HTTPS." if settings.SECURE_SSL_REDIRECT else "HTTPS redirect is not enabled.",
        },
        {
            "name": "Secure cookies",
            "status": "pass" if settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE else "warning",
            "detail": "Session and CSRF cookies use the Secure flag." if settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE else "Secure cookie flags are not both enabled.",
        },
        {
            "name": "HTTP Strict Transport Security",
            "status": "pass" if settings.SECURE_HSTS_SECONDS >= 15552000 else "warning",
            "detail": f"HSTS max-age is {settings.SECURE_HSTS_SECONDS} seconds.",
        },
        {
            "name": "Login lockout backend",
            "status": "pass" if "security.backends.LockoutModelBackend" in settings.AUTHENTICATION_BACKENDS else "fail",
            "detail": "Password logins use the monitored lockout backend." if "security.backends.LockoutModelBackend" in settings.AUTHENTICATION_BACKENDS else "The lockout authentication backend is not configured.",
        },
        {
            "name": "Public form email verification",
            "status": "pass" if "security.middleware.PublicEmailVerificationMiddleware" in settings.MIDDLEWARE else "fail",
            "detail": "Public form email addresses require a one-time inbox code." if "security.middleware.PublicEmailVerificationMiddleware" in settings.MIDDLEWARE else "Public email verification middleware is not configured.",
        },
    ]
    recommendations = [
        f"{check['name']}: {check['detail']}"
        for check in checks
        if check["status"] in {"warning", "fail"}
    ]
    return checks, recommendations


def build_security_snapshot():
    checks, recommendations = _security_checks()
    now = timezone.now()
    since = now - timedelta(hours=24)
    events = SecurityEvent.objects.filter(created_at__gte=since)
    locked_accounts = LoginAttemptState.objects.filter(locked_until__gt=now).count()
    event_counts = {
        severity: events.filter(severity=severity).count()
        for severity, _ in SecurityEvent.SEVERITY_CHOICES
    }
    failed_checks = sum(check["status"] == "fail" for check in checks)
    warning_checks = sum(check["status"] == "warning" for check in checks)
    score = max(0, 100 - failed_checks * 20 - warning_checks * 8 - event_counts["critical"] * 10 - event_counts["high"] * 5)
    summary = {
        "score": score,
        "events_24h": events.count(),
        "locked_accounts": locked_accounts,
        "high_events": event_counts["high"] + event_counts["critical"],
        "event_counts": event_counts,
        "checked_at": now.isoformat(),
    }
    return summary, checks, recommendations


def security_center(request):
    if not _can_view_security_center(request.user):
        return _forbidden(request)
    if request.method == "POST":
        if not request.user.is_superuser and not request.user.has_perm(
            "security.add_securityauditreport"
        ):
            return _forbidden(request)
        summary, checks, recommendations = build_security_snapshot()
        SecurityAuditReport.objects.create(
            generated_by=request.user,
            summary=summary,
            checks=checks,
            recommendations=recommendations,
        )
        messages.success(request, "Security audit report generated.")
        return redirect("security_center")

    summary, checks, recommendations = build_security_snapshot()
    return render(
        request,
        "security/security_center.html",
        {
            "summary": summary,
            "checks": checks,
            "recommendations": recommendations,
            "events": SecurityEvent.objects.order_by("-created_at")[:100],
            "reports": SecurityAuditReport.objects.select_related("generated_by")[:20],
        },
    )

