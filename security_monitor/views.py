
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SecurityFindingUpdateForm
from .models import SecurityAlertDelivery, SecurityFinding


def security_admin_required(view):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_staff,
        login_url="/dashboard/login/",
    )(view)


@login_required
@security_admin_required
def security_dashboard(request):
    base_findings = SecurityFinding.objects.all()
    findings = base_findings

    status = request.GET.get("status", "").strip()
    severity = request.GET.get("severity", "").strip()
    source = request.GET.get("source", "").strip()
    search = request.GET.get("q", "").strip()

    valid_statuses = {
        value for value, _ in SecurityFinding.Status.choices
    }
    valid_severities = {
        value for value, _ in SecurityFinding.Severity.choices
    }
    valid_sources = {
        value for value, _ in SecurityFinding.Source.choices
    }

    if status in valid_statuses:
        findings = findings.filter(status=status)

    if severity in valid_severities:
        findings = findings.filter(severity=severity)

    if source in valid_sources:
        findings = findings.filter(source=source)

    if search:
        findings = findings.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(path__icontains=search)
            | Q(source_ip__icontains=search)
        )

    active_statuses = [
        SecurityFinding.Status.OPEN,
        SecurityFinding.Status.INVESTIGATING,
    ]

    metrics = base_findings.aggregate(
        total=Count("id"),
        open=Count(
            "id",
            filter=Q(status=SecurityFinding.Status.OPEN),
        ),
        investigating=Count(
            "id",
            filter=Q(status=SecurityFinding.Status.INVESTIGATING),
        ),
        critical=Count(
            "id",
            filter=Q(
                severity=SecurityFinding.Severity.CRITICAL,
                status__in=active_statuses,
            ),
        ),
        resolved=Count(
            "id",
            filter=Q(status=SecurityFinding.Status.RESOLVED),
        ),
    )

    delivery_metrics = {
        "pending": SecurityAlertDelivery.objects.filter(
            status=SecurityAlertDelivery.Status.PENDING
        ).count(),
        "failed": SecurityAlertDelivery.objects.filter(
            status=SecurityAlertDelivery.Status.FAILED
        ).count(),
        "sent": SecurityAlertDelivery.objects.filter(
            status=SecurityAlertDelivery.Status.SENT
        ).count(),
    }

    paginator = Paginator(findings, 25)
    page_obj = paginator.get_page(request.GET.get("page"))


    context = {
        "total_findings": metrics["total"],
        "open_count": metrics["open"],
        "investigating_count": metrics["investigating"],
        "critical_count": metrics["critical"],
        "resolved_count": metrics["resolved"],
        "findings": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "delivery_metrics": delivery_metrics,
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
    form = SecurityFindingUpdateForm(
        request.POST,
        instance=finding,
    )

    if form.is_valid():
        finding = form.save(commit=False)

        if finding.status == SecurityFinding.Status.RESOLVED:
            if finding.resolved_at is None:
                finding.resolved_at = timezone.now()
            finding.resolved_by = request.user
        else:
            finding.resolved_at = None
            finding.resolved_by = None

        finding.save()
        messages.success(
            request,
            "Security finding status updated.",
        )
    else:
        messages.error(request, "Invalid status selection.")

    return redirect(
        f"{redirect('security_monitor:dashboard').url}"
        f"?{request.GET.urlencode()}"
        if request.GET
        else "security_monitor:dashboard"
    )


@login_required
@security_admin_required
@require_POST
def run_security_audit(request):
    import logging

    from .audits import (
        audit_django_configuration,
        audit_public_website,
    )

    logger = logging.getLogger(__name__)
    failed = False

    for audit in (
        audit_django_configuration,
        audit_public_website,
    ):
        try:
            audit()
        except Exception:
            failed = True
            logger.exception(
                "Dashboard security audit failed: %s",
                audit.__name__,
            )

    if failed:
        messages.warning(
            request,
            "The audit finished with errors. Check application logs.",
        )
    else:
        messages.success(
            request,
            "The website security audit finished.",
        )

    return redirect("security_monitor:dashboard")
