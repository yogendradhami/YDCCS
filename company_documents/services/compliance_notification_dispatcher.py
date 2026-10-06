from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from company_documents.services.compliance_notifications import (
    get_compliance_document_alerts,
    get_missing_compliance_alerts,
)
from notifications.models import Notification


User = get_user_model()

NOTIFICATION_TYPE = "system"


def get_compliance_recipients():
    return (
        User.objects.filter(
            is_active=True,
            is_staff=True,
        )
        .distinct()
    )


def _document_notification_exists_today(user, alert, title):
    today = timezone.localdate()

    document = alert["document"]

    link = reverse(
        "company_documents:detail",
        kwargs={"pk": document.pk},
    )

    return Notification.objects.filter(
        user=user,
        notification_type=NOTIFICATION_TYPE,
        title=title,
        link=link,
        created_at__date=today,
    ).exists()


def _missing_notification_exists_today(user, alert, title):
    today = timezone.localdate()

    link = _build_missing_alert_link(alert)

    return Notification.objects.filter(
        user=user,
        notification_type=NOTIFICATION_TYPE,
        title=title,
        link=link,
        created_at__date=today,
    ).exists()


def _build_missing_alert_link(alert):
    """
    Build a safe destination for a missing compliance notification.

    Employee alerts go directly to the employee compliance profile.
    Other scopes go to the main compliance overview.
    """
    entity = alert.get("entity")
    scope = alert.get("scope")

    if (
        scope == "employee"
        and entity is not None
        and getattr(entity, "pk", None)
    ):
        return reverse(
            "company_documents:employee_compliance",
            kwargs={"employee_id": entity.pk},
        )

    return reverse(
        "company_documents:compliance_overview",
    )


def _build_notification_message(alert):
    document = alert.get("document")

    if document is not None:
        related_name = alert.get(
            "related_name",
            "Company",
        )

        if alert["type"] == "expired":
            return (
                f"{document.name or document.original_filename} "
                f"has expired and requires immediate replacement. "
                f"Related record: {related_name}."
            )

        if alert["type"] == "review_due":
            return (
                f"{document.name or document.original_filename} "
                f"is due for review. "
                f"Related record: {related_name}."
            )

        if alert["type"] == "7_days":
            days = max(alert.get("days", 0), 0)

            if days == 0:
                timing = "today"
            elif days == 1:
                timing = "tomorrow"
            else:
                timing = f"in {days} days"

            return (
                f"{document.name or document.original_filename} "
                f"expires {timing}. "
                f"Related record: {related_name}."
            )

        if alert["type"] == "14_days":
            return (
                f"{document.name or document.original_filename} "
                f"expires in {alert.get('days', 0)} days. "
                f"Related record: {related_name}."
            )

        if alert["type"] == "30_days":
            return (
                f"{document.name or document.original_filename} "
                f"expires in {alert.get('days', 0)} days. "
                f"Related record: {related_name}."
            )

        return alert["message"]

    if alert["type"] == "missing":
        requirements = alert.get("requirements", [])
        entity_name = alert.get(
            "entity_name",
            "this record",
        )

        if len(requirements) == 1:
            requirement_text = requirements[0]
        else:
            requirement_text = ", ".join(requirements)

        return (
            f"{entity_name} is missing required compliance documentation: "
            f"{requirement_text}."
        )

    return alert.get("message", "Compliance attention required.")


@transaction.atomic
def dispatch_compliance_notifications():
    """
    Create persistent in-app notifications for:

    1. Expired/review/expiring documents.
    2. Required compliance documents that are missing.

    Missing requirements are grouped by entity to avoid notification spam.
    """
    document_alerts = get_compliance_document_alerts()
    missing_alerts = get_missing_compliance_alerts()

    recipients = list(get_compliance_recipients())

    created = 0
    skipped = 0

    notification_url = reverse(
        "company_documents:compliance_notifications"
    )

    # ---------------------------------------------------------
    # DOCUMENT EXPIRY / REVIEW ALERTS
    # ---------------------------------------------------------

    for alert in document_alerts:
        document = alert["document"]

        title = f"Compliance: {alert['title']}"

        detail_url = reverse(
            "company_documents:detail",
            kwargs={"pk": document.pk},
        )

        message = _build_notification_message(alert)

        for user in recipients:
            if _document_notification_exists_today(
                user,
                alert,
                title,
            ):
                skipped += 1
                continue

            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=NOTIFICATION_TYPE,
                link=detail_url,
            )

            created += 1

    # ---------------------------------------------------------
    # MISSING REQUIREMENT ALERTS
    # ---------------------------------------------------------

    for alert in missing_alerts:
        entity_name = alert["entity_name"]
        count = alert["requirement_count"]

        title = (
            f"Compliance: {count} missing "
            f"requirement"
            f"{'s' if count != 1 else ''} — "
            f"{entity_name}"
        )

        link = _build_missing_alert_link(alert)

        message = _build_notification_message(alert)

        for user in recipients:
            if _missing_notification_exists_today(
                user,
                alert,
                title,
            ):
                skipped += 1
                continue

            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=NOTIFICATION_TYPE,
                link=link,
            )

            created += 1

    return {
        "document_alerts_found": len(document_alerts),
        "missing_alerts_found": len(missing_alerts),
        "alerts_found": (
            len(document_alerts) +
            len(missing_alerts)
        ),
        "recipients": len(recipients),
        "notifications_created": created,
        "duplicates_skipped": skipped,
        "notification_center_url": notification_url,
    }