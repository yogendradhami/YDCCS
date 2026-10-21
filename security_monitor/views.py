
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SecurityFindingUpdateForm
from .models import SecurityFinding


def security_admin_required(view):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_staff,
        login_url="/dashboard/login/",
    )(view)


@login_required
@security_admin_required
def security_dashboard(request):
    findings = SecurityFinding.objects.all()

    status = request.GET.get("status", "")
    severity = request.GET.get("severity", "")
    source = request.GET.get("source", "")
    search = request.GET.get("q", "").strip()

    valid_statuses = {value for value, _ in SecurityFinding.Status.choices}
    valid_severities = {
        value for value, _ in SecurityFinding.Severity.choices
    }
    valid_sources = {value for value, _ in SecurityFinding.Source.choices}

    if status in valid_statuses:
        findings = findings.filter(status=status)

    if severity in valid_severities:
        findings = findings.filter(severity=severity)

    if source in valid_sources:
        findings = findings.filter(source=source)

    if search:
        findings = findings.filter(title__icontains=search)

    counts = SecurityFinding.objects.aggregate(
        total=Count("id"),
    )

    open_count = SecurityFinding.objects.filter(
        status=SecurityFinding.Status.OPEN
    ).count()

    critical_count = SecurityFinding.objects.filter(
        severity=SecurityFinding.Severity.CRITICAL,
        status__in=[
            SecurityFinding.Status.OPEN,
            SecurityFinding.Status.INVESTIGATING,
        ],
    ).count()

    context = {
        "findings": findings[:200],
        "total_findings": counts["total"],
        "open_count": open_count,
        "critical_count": critical_count,
        "statuses": SecurityFinding.Status.choices,
        "severities": SecurityFinding.Severity.choices,
        "sources": SecurityFinding.Source.choices,
        "selected_status": status,
        "selected_severity": severity,
        "selected_source": source,
        "search_query": search,
    }
    return render(
        request,
        "security_monitor/dashboard.html",
        context,
    )


@login_required
@security_admin_required
@require_POST
def update_finding(request, pk):
    finding = get_object_or_404(SecurityFinding, pk=pk)
    form = SecurityFindingUpdateForm(request.POST, instance=finding)

    if form.is_valid():
        finding = form.save(commit=False)

        if finding.status == SecurityFinding.Status.RESOLVED:
            finding.resolved_at = timezone.now()
            finding.resolved_by = request.user
        else:
            finding.resolved_at = None
            finding.resolved_by = None

        finding.save()
        messages.success(request, "Security finding status updated.")
    else:
        messages.error(request, "Invalid status selection.")

    return redirect("security_monitor:dashboard")


@login_required
@security_admin_required
@require_POST
def run_security_audit(request):
    from .audits import audit_django_configuration, audit_public_website

    for audit in (audit_django_configuration, audit_public_website):
        try:
            audit()
        except Exception:
            # Keep a failure in the service logs and still run the other check.
            import logging

            logging.getLogger(__name__).exception(
                "Dashboard security audit failed: %s", audit.__name__
            )

    messages.success(request, "The website security audit finished.")
    return redirect("security_monitor:dashboard")
