from dataclasses import dataclass

from django.db.models import Q

from employees.models import Employee

from company_documents.services.compliance_requirements import (
    build_scope_report,
)


@dataclass
class EmployeeComplianceMatrixRow:
    employee: object
    summary: dict
    results: list


def build_employee_compliance_matrix():
    """
    Build a compliance matrix for every employee.

    The existing compliance requirement engine remains the
    source of truth. This service only reshapes the existing
    compliance results for matrix presentation.
    """

    reports = build_scope_report("employee")

    rows = []

    for record in reports:
        employee = record.get("entity")
        summary = record.get("summary", {})
        results = record.get("results", [])

        if employee is None:
            continue

        rows.append(
            EmployeeComplianceMatrixRow(
                employee=employee,
                summary=summary,
                results=results,
            )
        )

    return rows


def filter_employee_compliance_matrix(
    rows,
    search_query="",
    status_filter="",
):
    """
    Filter matrix rows without changing the underlying
    compliance evaluation logic.
    """

    search_query = (search_query or "").strip().lower()
    status_filter = (status_filter or "").strip().lower()

    filtered = []

    for row in rows:
        employee = row.employee
        summary = row.summary

        if search_query:
            searchable_values = [
                getattr(employee, "full_name", ""),
                getattr(employee, "email", ""),
                getattr(employee, "role", ""),
            ]

            searchable_text = " ".join(
                str(value or "")
                for value in searchable_values
            ).lower()

            if search_query not in searchable_text:
                continue

        if status_filter:
            if status_filter == "compliant":
                if not summary.get("has_applicable_requirements"):
                    continue

                if summary.get("actionable", 0) != 0:
                    continue

            elif status_filter == "attention":
                if summary.get("actionable", 0) <= 0:
                    continue

            elif status_filter == "missing":
                if summary.get("missing", 0) <= 0:
                    continue

            elif status_filter == "expired":
                if summary.get("expired", 0) <= 0:
                    continue

            elif status_filter == "review_due":
                if summary.get("review_due", 0) <= 0:
                    continue

            elif status_filter == "expiring":
                if summary.get("expiring", 0) <= 0:
                    continue

            elif status_filter == "no_requirements":
                if summary.get("has_applicable_requirements"):
                    continue

        filtered.append(row)

    return filtered


def summarize_employee_compliance_matrix(rows):
    """
    Build KPI totals for the matrix header.
    """

    summary = {
        "total_employees": len(rows),
        "compliant": 0,
        "attention": 0,
        "missing": 0,
        "expired": 0,
        "review_due": 0,
        "expiring": 0,
        "no_requirements": 0,
    }

    for row in rows:
        employee_summary = row.summary

        if not employee_summary.get(
            "has_applicable_requirements"
        ):
            summary["no_requirements"] += 1
            continue

        if employee_summary.get("actionable", 0) > 0:
            summary["attention"] += 1
        else:
            summary["compliant"] += 1

        summary["missing"] += employee_summary.get(
            "missing",
            0,
        )

        summary["expired"] += employee_summary.get(
            "expired",
            0,
        )

        summary["review_due"] += employee_summary.get(
            "review_due",
            0,
        )

        summary["expiring"] += employee_summary.get(
            "expiring",
            0,
        )

    return summary