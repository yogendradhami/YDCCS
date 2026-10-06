from datetime import timedelta

from django.utils import timezone

from company_documents.models import CompanyDocument


PRIORITY_ORDER = {
    "expired": 1,
    "missing": 2,
    "review_due": 3,
    "7_days": 4,
    "14_days": 5,
    "30_days": 6,
}


def _document_name(document):
    return document.name or document.original_filename or "Untitled document"


def _related_name(document):
    try:
        return document.related_name
    except Exception:
        return "Company"


def _build_document_alert(document):
    today = timezone.localdate()

    if document.status != CompanyDocument.Status.ACTIVE:
        return None

    if document.expiry_date and document.expiry_date < today:
        return {
            "type": "expired",
            "priority": PRIORITY_ORDER["expired"],
            "severity": "critical",
            "title": "Document expired",
            "message": (
                f"{_document_name(document)} has expired "
                f"and requires immediate replacement."
            ),
            "document": document,
            "related_name": _related_name(document),
            "days": document.days_until_expiry,
            "action_label": "Replace document",
            "action_url": f"/dashboard/company-documents/{document.pk}/edit/",
        }

    if document.review_date and document.review_date <= today:
        return {
            "type": "review_due",
            "priority": PRIORITY_ORDER["review_due"],
            "severity": "warning",
            "title": "Document review due",
            "message": (
                f"{_document_name(document)} is due for review."
            ),
            "document": document,
            "related_name": _related_name(document),
            "days": (
                document.review_date - today
            ).days,
            "action_label": "Review document",
            "action_url": f"/dashboard/company-documents/{document.pk}/edit/",
        }

    if document.expiry_date:
        days = (document.expiry_date - today).days

        if days <= 7:
            return {
                "type": "7_days",
                "priority": PRIORITY_ORDER["7_days"],
                "severity": "critical",
                "title": "Expires within 7 days",
                "message": (
                    f"{_document_name(document)} expires in "
                    f"{max(days, 0)} days."
                ),
                "document": document,
                "related_name": _related_name(document),
                "days": days,
                "action_label": "Renew document",
                "action_url": f"/dashboard/company-documents/{document.pk}/edit/",
            }

        if days <= 14:
            return {
                "type": "14_days",
                "priority": PRIORITY_ORDER["14_days"],
                "severity": "warning",
                "title": "Expires within 14 days",
                "message": (
                    f"{_document_name(document)} expires in "
                    f"{days} days."
                ),
                "document": document,
                "related_name": _related_name(document),
                "days": days,
                "action_label": "Review renewal",
                "action_url": f"/dashboard/company-documents/{document.pk}/edit/",
            }

        if days <= 30:
            return {
                "type": "30_days",
                "priority": PRIORITY_ORDER["30_days"],
                "severity": "notice",
                "title": "Expires within 30 days",
                "message": (
                    f"{_document_name(document)} expires in "
                    f"{days} days."
                ),
                "document": document,
                "related_name": _related_name(document),
                "days": days,
                "action_label": "Plan renewal",
                "action_url": f"/dashboard/company-documents/{document.pk}/edit/",
            }

    return None


def get_compliance_document_alerts():
    """
    Return live compliance alerts for active company documents.

    Alerts are calculated from the current database state.
    No duplicate notification records are created.
    """

    documents = (
        CompanyDocument.objects
        .filter(
            status=CompanyDocument.Status.ACTIVE,
        )
        .select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
        )
        .order_by("expiry_date", "name")
    )

    alerts = []

    for document in documents:
        alert = _build_document_alert(document)

        if alert:
            alerts.append(alert)

    alerts.sort(
        key=lambda item: (
            item["priority"],
            item["days"]
            if item["days"] is not None
            else 999999,
            item["document"].name.lower(),
        )
    )

    return alerts


def get_compliance_notification_summary(alerts=None):
    if alerts is None:
        alerts = get_compliance_document_alerts()

    return {
        "total": len(alerts),
        "critical": sum(
            1
            for alert in alerts
            if alert["severity"] == "critical"
        ),
        "warning": sum(
            1
            for alert in alerts
            if alert["severity"] == "warning"
        ),
        "notice": sum(
            1
            for alert in alerts
            if alert["severity"] == "notice"
        ),
        "expired": sum(
            1
            for alert in alerts
            if alert["type"] == "expired"
        ),
        "review_due": sum(
            1
            for alert in alerts
            if alert["type"] == "review_due"
        ),
        "within_7_days": sum(
            1
            for alert in alerts
            if alert["type"] == "7_days"
        ),
        "within_14_days": sum(
            1
            for alert in alerts
            if alert["type"] == "14_days"
        ),
        "within_30_days": sum(
            1
            for alert in alerts
            if alert["type"] == "30_days"
        ),
    }


from collections import defaultdict

from company_documents.models import ComplianceRequirement


def get_missing_compliance_alerts():
    """
    Build grouped compliance alerts for required documents that are missing.

    Uses the existing compliance engine so notification results stay
    synchronized with Compliance Overview.
    """
    from company_documents.services.compliance_requirements import (
        build_overall_report,
    )

    report = build_overall_report()
    alerts = []

    scope_labels = {
        ComplianceRequirement.Scope.COMPANY: "Company",
        ComplianceRequirement.Scope.EMPLOYEE: "Employee",
        ComplianceRequirement.Scope.CUSTOMER: "Customer",
        ComplianceRequirement.Scope.VEHICLE: "Vehicle",
        ComplianceRequirement.Scope.SUPPLIER: "Supplier",
        ComplianceRequirement.Scope.CONTRACT: "Contract",
    }

    for scope, entity_groups in report.get("scopes", {}).items():
        # Company scope is represented by entity=None.
        for group in entity_groups:
            entity = group.get("entity")
            results = group.get("results", [])

            missing_results = [
                result
                for result in results
                if (
                    result.status == "missing"
                    and result.requirement.required
                )
            ]

            if not missing_results:
                continue

            scope_label = scope_labels.get(
                scope,
                str(scope).replace("_", " ").title(),
            )

            if entity is None:
                entity_name = "YD Commercial Cleaning"
            else:
                entity_name = str(entity)

            requirement_names = [
                result.requirement.name
                for result in missing_results
            ]

            alerts.append(
                {
                    "type": "missing",
                    "severity": "critical",
                    "priority": 2,
                    "scope": scope,
                    "scope_label": scope_label,
                    "entity": entity,
                    "entity_name": entity_name,
                    "related_name": entity_name,
                    "requirement_count": len(requirement_names),
                    "requirements": requirement_names,
                    "title": (
                        f"{len(requirement_names)} compliance "
                        f"requirement"
                        f"{'s' if len(requirement_names) != 1 else ''} "
                        f"missing"
                    ),
                    "message": (
                        f"{entity_name} is missing "
                        f"{len(requirement_names)} required "
                        f"compliance document"
                        f"{'s' if len(requirement_names) != 1 else ''}."
                    ),
                }
            )

    alerts.sort(
        key=lambda alert: (
            alert["priority"],
            alert["scope_label"],
            alert["entity_name"].lower(),
        )
    )

    return alerts