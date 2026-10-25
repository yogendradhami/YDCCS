from datetime import timedelta

from django.contrib.auth.models import Permission
from django.utils import timezone

from security.services import identifier_digest


def grant_dashboard_permissions(user, *permission_labels):
    """Grant a test user only the dashboard permissions a scenario needs."""
    labels = {"security.access_dashboard", *permission_labels}
    permissions = []

    for label in labels:
        app_label, codename = label.split(".", maxsplit=1)
        permissions.append(
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
        )

    user.user_permissions.add(*permissions)
    return user


def mark_public_email_verified(client, email):
    """Seed the same short-lived receipt written after a valid email code."""
    session = client.session
    session["verified_public_email"] = {
        "emails": [
            {
                "email_hash": identifier_digest(email),
                "expires_at": (timezone.now() + timedelta(minutes=20)).timestamp(),
            }
        ]
    }
    session.save()
