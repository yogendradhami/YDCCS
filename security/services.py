import hashlib
import ipaddress
import logging
import re
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import LoginAttemptState, SecurityEvent

logger = logging.getLogger(__name__)

LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_DURATION = timedelta(minutes=30)
LOGIN_FAILURE_WINDOW = timedelta(minutes=30)


def normalize_login_identifier(identifier):
    return re.sub(r"\s+", "", str(identifier or "")).casefold()


def identifier_digest(identifier):
    normalized = normalize_login_identifier(identifier)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def request_ip(request):
    if not request:
        return None
    raw_ip = request.META.get("REMOTE_ADDR", "").strip()
    try:
        return str(ipaddress.ip_address(raw_ip))
    except ValueError:
        return None


def record_security_event(
    event_type,
    description,
    *,
    request=None,
    severity="medium",
    identifier_hash="",
    path="",
):
    try:
        return SecurityEvent.objects.create(
            event_type=event_type,
            severity=severity,
            source_ip=request_ip(request),
            identifier_hash=identifier_hash,
            path=(path or getattr(request, "path", ""))[:500],
            description=description[:500],
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:500],
        )
    except Exception:
        # Monitoring failure should not prevent authentication or a public
        # page from responding. The process log still records the failure.
        logger.exception("Could not persist a security event: %s", event_type)
        return None


def login_lock_state(identifier):
    key = identifier_digest(identifier)
    try:
        state = LoginAttemptState.objects.filter(identifier_hash=key).first()
        now = timezone.now()
        if not state or not state.locked_until or state.locked_until <= now:
            return key, None
        return key, state
    except Exception:
        logger.exception("Could not read login lockout state.")
        # Fail closed if a request cannot confirm whether an account is locked.
        state = LoginAttemptState(
            identifier_hash=key,
            locked_until=timezone.now() + LOGIN_LOCKOUT_DURATION,
        )
        return key, state


def record_failed_login(identifier, request=None):
    key = identifier_digest(identifier)
    now = timezone.now()
    ip = request_ip(request)

    try:
        with transaction.atomic():
            state = (
                LoginAttemptState.objects.select_for_update()
                .filter(identifier_hash=key)
                .first()
            )
            if state is None:
                try:
                    # Keep the uniqueness race inside a savepoint so a
                    # concurrent insert does not poison the outer transaction.
                    with transaction.atomic():
                        state = LoginAttemptState.objects.create(
                            identifier_hash=key,
                            failure_count=0,
                            window_started_at=now,
                            last_failed_at=now,
                            last_ip=ip,
                        )
                except IntegrityError:
                    state = LoginAttemptState.objects.select_for_update().get(
                        identifier_hash=key
                    )

            if state.locked_until and state.locked_until > now:
                return key, state.locked_until, False

            if now - state.window_started_at >= LOGIN_FAILURE_WINDOW:
                state.failure_count = 0
                state.window_started_at = now
                state.locked_until = None

            state.failure_count += 1
            state.last_failed_at = now
            state.last_ip = ip

            was_locked = False
            if state.failure_count >= LOGIN_LOCKOUT_THRESHOLD:
                state.locked_until = now + LOGIN_LOCKOUT_DURATION
                was_locked = True

            state.save(
                update_fields=[
                    "failure_count",
                    "window_started_at",
                    "locked_until",
                    "last_failed_at",
                    "last_ip",
                    "updated_at",
                ]
            )

        if was_locked:
            record_security_event(
                "login_lockout",
                "An account identifier was locked after five failed login attempts.",
                request=request,
                severity="high",
                identifier_hash=key,
            )

        return key, state.locked_until, was_locked
    except Exception:
        logger.exception("Could not update login lockout state.")
        # Fail closed: authentication attempts are rejected when lockout
        # tracking is unavailable.
        return key, now + LOGIN_LOCKOUT_DURATION, False


def clear_login_failures(identifier):
    LoginAttemptState.objects.filter(
        identifier_hash=identifier_digest(identifier),
    ).delete()


def clear_user_login_lock(user):
    identifier = getattr(user, "get_username", lambda: "")()
    if identifier:
        clear_login_failures(identifier)


def limit_cache_counter(key, limit, timeout):
    try:
        if cache.add(key, 1, timeout=timeout):
            return True
        value = cache.incr(key)
        return value <= limit
    except Exception:
        logger.exception("Security rate-limit storage is unavailable.")
        return False

