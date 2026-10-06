from company_documents.models import CompanyDocument, ComplianceRequirement
from company_documents.services.compliance_requirements import (
    evaluate_requirements,
    summarize_results,
)


def get_employee_requirements():
    """
    Return active employee compliance requirements.
    """
    return ComplianceRequirement.objects.filter(
        scope=ComplianceRequirement.Scope.EMPLOYEE,
        active=True,
    ).order_by(
        "sort_order",
        "name",
    )


def build_employee_compliance_profile(employee):
    """
    Build the complete compliance profile for one employee.

    Uses the existing CompanyDocument and ComplianceRequirement
    systems. No duplicate employee-document records are created.
    """

    requirements = get_employee_requirements()

    results = evaluate_requirements(
        requirements=requirements,
        entity=employee,
    )

    summary = summarize_results(results)

    documents = (
        CompanyDocument.objects
        .filter(
            status=CompanyDocument.Status.ACTIVE,
            employee=employee,
            related_type=CompanyDocument.RelatedType.EMPLOYEE,
        )
        .order_by(
            "-updated_at",
        )
    )

    return {
        "employee": employee,
        "requirements": requirements,
        "results": results,
        "summary": summary,
        "documents": documents,
    }