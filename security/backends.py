import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils import timezone

from .models import LoginAttemptState
from .services import (
    clear_login_failures,
    identifier_digest,
    login_lock_state,
    record_failed_login,
    record_security_event,
)

logger = logging.getLogger(__name__)


class LockoutModelBackend(ModelBackend):
    """Django's model backend with persistent account lockout tracking."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = username or kwargs.get(UserModel.USERNAME_FIELD) or ""
        identifier = str(identifier).strip()
        if not identifier or password is None:
            return None

        account = UserModel._default_manager.filter(
            Q(**{f"{UserModel.USERNAME_FIELD}__iexact": identifier})
        ).first()
        if account is None and "@" in identifier:
            account = UserModel._default_manager.filter(
                email__iexact=identifier,
            ).first()

        canonical_identifier = account.get_username() if account else identifier
        identifier_key, lock_state = login_lock_state(canonical_identifier)
        if lock_state:
            # Limit repeated lockout records to one event per identifier/IP
            # every 10 minutes while keeping each request blocked.
            from .services import limit_cache_counter

            if limit_cache_counter(
                f"security:locked-login:{identifier_key}",
                1,
                600,
            ):
                record_security_event(
                    "locked_login",
                    "A login attempt was rejected while the account lock was active.",
                    request=request,
                    severity="medium",
                    identifier_hash=identifier_key,
                )
            return None

        auth_username = account.get_username() if account else identifier
        authenticated_user = super().authenticate(
            request,
            username=auth_username,
            password=password,
            **{
                key: value
                for key, value in kwargs.items()
                if key != UserModel.USERNAME_FIELD
            },
        )

        if authenticated_user is not None:
            clear_login_failures(canonical_identifier)
            return authenticated_user

        _, locked_until, is_new_lock = record_failed_login(
            canonical_identifier,
            request,
        )
        if is_new_lock:
            logger.warning(
                "Login lockout activated for identifier hash %s until %s",
                identifier_key,
                locked_until,
            )
        return None

