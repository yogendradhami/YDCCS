from django.db.models import Q

from company_documents.models import CompanyDocument, ComplianceRequirement
from company_documents.services.compliance_requirements import (
    STATUS_NOT_APPLICABLE,
    evaluate_document,
    evaluate_requirements,
    summarize_results,
)


def get_document_entity(document):
    if document.related_type == CompanyDocument.RelatedType.EMPLOYEE:
        return document.employee

    if document.related_type == CompanyDocument.RelatedType.CUSTOMER:
        return document.customer

    if document.related_type == CompanyDocument.RelatedType.VEHICLE:
        return document.vehicle

    if document.related_type == CompanyDocument.RelatedType.SUPPLIER:
        return document.supplier

    if document.related_type == CompanyDocument.RelatedType.CONTRACT:
        return document.contract

    return None


def get_document_scope(document):
    scope_by_related_type = {
        CompanyDocument.RelatedType.COMPANY: ComplianceRequirement.Scope.COMPANY,
        CompanyDocument.RelatedType.EMPLOYEE: ComplianceRequirement.Scope.EMPLOYEE,
        CompanyDocument.RelatedType.CUSTOMER: ComplianceRequirement.Scope.CUSTOMER,
        CompanyDocument.RelatedType.VEHICLE: ComplianceRequirement.Scope.VEHICLE,
        CompanyDocument.RelatedType.SUPPLIER: ComplianceRequirement.Scope.SUPPLIER,
        CompanyDocument.RelatedType.CONTRACT: ComplianceRequirement.Scope.CONTRACT,
    }

    return scope_by_related_type.get(document.related_type)


def get_affected_requirements(document):
    scope = get_document_scope(document)

    if not scope:
        return ComplianceRequirement.objects.none()

    queryset = ComplianceRequirement.objects.filter(
        active=True,
        scope=scope,
    )

    if document.category:
        queryset = queryset.filter(
            Q(category="")
            | Q(category__iexact=document.category)
        )

    if document.document_type:
        queryset = queryset.filter(
            Q(document_type="")
            | Q(document_type__iexact=document.document_type)
        )

    return queryset.order_by(
        "sort_order",
        "name",
    )


def resolve_document_compliance(document):
    """
    Re-evaluate compliance requirements affected by a document change.

    The existing compliance requirement engine remains the source of
    truth. This function derives the current state from
    ComplianceRequirement + CompanyDocument without storing duplicate
    compliance status records.
    """

    requirements = get_affected_requirements(document)
    entity = get_document_entity(document)
    results = evaluate_requirements(
        requirements=requirements,
        entity=entity,
    )

    if not results:
        status, message = evaluate_document(document)

        return {
            "status": STATUS_NOT_APPLICABLE,
            "document_status": status,
            "message": message,
            "entity": entity,
            "requirements": requirements,
            "results": [],
            "summary": summarize_results([]),
        }

    summary = summarize_results(results)

    if summary.get("actionable", 0):
        if summary.get("expired", 0):
            status = "expired"
        elif summary.get("review_due", 0):
            status = "review_due"
        elif summary.get("expiring", 0):
            status = "expiring"
        else:
            status = "missing"
    else:
        status = "satisfied"

    return {
        "status": status,
        "document_status": status,
        "message": "Compliance has been evaluated against current active documents.",
        "entity": entity,
        "requirements": requirements,
        "results": results,
        "summary": summary,
    }
