from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from company_documents.models import (
    CompanyDocument,
    ComplianceRequirement,
)


@dataclass
class ComplianceResult:
    requirement: ComplianceRequirement
    entity: object | None
    status: str
    document: CompanyDocument | None = None
    message: str = ""


STATUS_SATISFIED = "satisfied"
STATUS_MISSING = "missing"
STATUS_EXPIRED = "expired"
STATUS_REVIEW_DUE = "review_due"
STATUS_EXPIRING = "expiring"
STATUS_NOT_APPLICABLE = "not_applicable"


def get_requirement_queryset(scope=None):
    queryset = ComplianceRequirement.objects.filter(
        active=True,
    )

    if scope:
        queryset = queryset.filter(
            scope=scope,
        )

    return queryset.order_by(
        "scope",
        "sort_order",
        "name",
    )


def get_entity_id(entity):
    if entity is None:
        return None

    return getattr(
        entity,
        "pk",
        None,
    )


def get_entity_document_filter(scope, entity):
    """
    Return the CompanyDocument relationship filter for an entity.
    """

    entity_id = get_entity_id(entity)

    if not entity_id:
        return Q(
            related_type=CompanyDocument.RelatedType.COMPANY,
        )

    if scope == ComplianceRequirement.Scope.COMPANY:
        return Q(
            related_type=CompanyDocument.RelatedType.COMPANY,
        )

    if scope == ComplianceRequirement.Scope.EMPLOYEE:
        return Q(
            related_type=CompanyDocument.RelatedType.EMPLOYEE,
            employee_id=entity_id,
        )

    if scope == ComplianceRequirement.Scope.CUSTOMER:
        return Q(
            related_type=CompanyDocument.RelatedType.CUSTOMER,
            customer_id=entity_id,
        )

    if scope == ComplianceRequirement.Scope.VEHICLE:
        return Q(
            related_type=CompanyDocument.RelatedType.VEHICLE,
            vehicle_id=entity_id,
        )

    if scope == ComplianceRequirement.Scope.SUPPLIER:
        return Q(
            related_type=CompanyDocument.RelatedType.SUPPLIER,
            supplier_id=entity_id,
        )

    if scope == ComplianceRequirement.Scope.CONTRACT:
        return Q(
            related_type=CompanyDocument.RelatedType.CONTRACT,
            contract_id=entity_id,
        )

    return Q(pk__isnull=True)


def find_matching_document(requirement, entity=None):
    """
    Find the best active CompanyDocument matching a requirement.

    Matching uses:
        1. Correct relationship
        2. Matching category when configured
        3. Matching document type when configured
        4. Latest updated document wins
    """

    relationship_filter = get_entity_document_filter(
        requirement.scope,
        entity,
    )

    queryset = (
        CompanyDocument.objects
        .filter(
            status=CompanyDocument.Status.ACTIVE,
        )
        .filter(
            relationship_filter,
        )
    )

    if requirement.category:
        queryset = queryset.filter(
            category__iexact=requirement.category,
        )

    if requirement.document_type:
        queryset = queryset.filter(
            document_type__iexact=requirement.document_type,
        )

    return (
        queryset
        .order_by(
            "-updated_at",
            "-version",
            "-id",
        )
        .first()
    )


def evaluate_document(document):
    """
    Convert a matched CompanyDocument into a compliance state.
    """

    if not document:
        return STATUS_MISSING, "Required document is missing."

    health = document.health_status

    if health == "expired":
        return (
            STATUS_EXPIRED,
            "Required document has expired.",
        )

    if health == "review_due":
        return (
            STATUS_REVIEW_DUE,
            "Required document is due for review.",
        )

    if health == "expiring":
        return (
            STATUS_EXPIRING,
            "Required document expires within 30 days.",
        )

    if health == "inactive":
        return (
            STATUS_MISSING,
            "The matching document is inactive.",
        )

    return (
        STATUS_SATISFIED,
        "Requirement is satisfied.",
    )


def evaluate_requirement(requirement, entity=None):
    """
    Evaluate one compliance requirement.
    """

    document = find_matching_document(
        requirement,
        entity=entity,
    )

    status, message = evaluate_document(
        document,
    )

    return ComplianceResult(
        requirement=requirement,
        entity=entity,
        status=status,
        document=document,
        message=message,
    )


def evaluate_requirements(requirements, entity=None):
    """
    Evaluate a collection of requirements for one entity.
    """

    results = []

    for requirement in requirements:

        results.append(
            evaluate_requirement(
                requirement,
                entity=entity,
            )
        )

    return results

def summarize_results(results):
    """
    Return compliance statistics.

    Optional requirements are excluded from the compliance denominator.
    They remain available for informational purposes but do not reduce
    the compliance percentage.

    Scopes with no applicable entities are represented as N/A rather
    than incorrectly receiving a 100% compliance score.
    """

    summary = {
        "total": 0,
        "satisfied": 0,
        "missing": 0,
        "expired": 0,
        "review_due": 0,
        "expiring": 0,
        "optional_total": 0,
        "optional_satisfied": 0,
        "optional_missing": 0,
        "not_applicable": 0,
    }

    for result in results:

        requirement = result.requirement

        if not requirement.required:

            summary["optional_total"] += 1

            if result.status == STATUS_SATISFIED:
                summary["optional_satisfied"] += 1

            elif result.status == STATUS_MISSING:
                summary["optional_missing"] += 1

            continue

        summary["total"] += 1

        if result.status == STATUS_SATISFIED:
            summary["satisfied"] += 1

        elif result.status == STATUS_MISSING:
            summary["missing"] += 1

        elif result.status == STATUS_EXPIRED:
            summary["expired"] += 1

        elif result.status == STATUS_REVIEW_DUE:
            summary["review_due"] += 1

        elif result.status == STATUS_EXPIRING:
            summary["expiring"] += 1

        elif result.status == STATUS_NOT_APPLICABLE:
            summary["not_applicable"] += 1

    summary["actionable"] = (
        summary["missing"]
        + summary["expired"]
        + summary["review_due"]
        + summary["expiring"]
    )

    if summary["total"]:

        summary["percentage"] = round(
            (
                summary["satisfied"]
                / summary["total"]
            )
            * 100
        )

        summary["has_applicable_requirements"] = True

    else:

        summary["percentage"] = None

        summary["has_applicable_requirements"] = False

    return summary


def get_scope_entities(scope):
    """
    Return active/current entities for a compliance scope.

    Imports are intentionally local to avoid unnecessary model
    loading and circular import problems.
    """

    if scope == ComplianceRequirement.Scope.EMPLOYEE:

        from employees.models import Employee

        return Employee.objects.filter(
            active=True,
        ).order_by(
            "full_name",
        )

    if scope == ComplianceRequirement.Scope.CUSTOMER:

        from customers.models import Customer

        return Customer.objects.order_by(
            "full_name",
        )

    if scope == ComplianceRequirement.Scope.VEHICLE:

        from dashboard.models import Vehicle

        return Vehicle.objects.order_by(
            "vehicle_name",
        )

    if scope == ComplianceRequirement.Scope.SUPPLIER:

        from dashboard.models import Supplier

        return Supplier.objects.filter(
            active=True,
        ).order_by(
            "name",
        )

    if scope == ComplianceRequirement.Scope.CONTRACT:

        from contracts.models import CleaningContract

        return CleaningContract.objects.exclude(
            status__iexact="cancelled",
        ).select_related(
            "customer",
        ).order_by(
            "customer__full_name",
            "service_type",
        )

    return []


def build_scope_report(scope):
    """
    Build a compliance report for an entire scope.
    """

    requirements = list(
        get_requirement_queryset(
            scope=scope,
        )
    )

    if scope == ComplianceRequirement.Scope.COMPANY:

        results = evaluate_requirements(
            requirements,
            entity=None,
        )

        return [
            {
                "entity": None,
                "results": results,
                "summary": summarize_results(results),
            }
        ]

    entities = get_scope_entities(
        scope,
    )

    report = []

    for entity in entities:

        results = evaluate_requirements(
            requirements,
            entity=entity,
        )

        report.append(
            {
                "entity": entity,
                "results": results,
                "summary": summarize_results(results),
            }
        )

    return report


def build_overall_report():
    """
    Build the complete compliance overview.
    """

    scopes = [
        ComplianceRequirement.Scope.COMPANY,
        ComplianceRequirement.Scope.EMPLOYEE,
        ComplianceRequirement.Scope.VEHICLE,
        ComplianceRequirement.Scope.CUSTOMER,
        ComplianceRequirement.Scope.SUPPLIER,
        ComplianceRequirement.Scope.CONTRACT,
    ]

    overall_results = []

    scope_reports = {}

    for scope in scopes:

        report = build_scope_report(
            scope,
        )

        scope_reports[scope] = report

        for item in report:
            overall_results.extend(
                item["results"]
            )

    summary = summarize_results(
        overall_results,
    )

    return {
        "summary": summary,
        "scopes": scope_reports,
    }