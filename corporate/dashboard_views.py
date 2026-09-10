from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import CorporateLead


@login_required
def corporate_lead_list(request):
    """
    Corporate B2B lead dashboard.

    Keeps CorporateLead completely separate from the existing
    QuoteRequest / standard lead system.
    """

    leads = CorporateLead.objects.select_related("assigned_to").all()

    # ---------------------------------------------------------
    # Search
    # ---------------------------------------------------------
    search_query = request.GET.get("q", "").strip()

    if search_query:
        leads = leads.filter(
            Q(full_name__icontains=search_query)
            | Q(company_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(industry__icontains=search_query)
            | Q(service_locations__icontains=search_query)
        )

    # ---------------------------------------------------------
    # Status filter
    # ---------------------------------------------------------
    status_filter = request.GET.get("status", "").strip()

    valid_statuses = {
        choice[0]
        for choice in CorporateLead.STATUS_CHOICES
    }

    if status_filter in valid_statuses:
        leads = leads.filter(status=status_filter)

    # ---------------------------------------------------------
    # Lead type filter
    # ---------------------------------------------------------
    lead_type_filter = request.GET.get("lead_type", "").strip()

    valid_lead_types = {
        choice[0]
        for choice in CorporateLead.LEAD_TYPE_CHOICES
    }

    if lead_type_filter in valid_lead_types:
        leads = leads.filter(lead_type=lead_type_filter)

    # ---------------------------------------------------------
    # Assigned staff filter
    # ---------------------------------------------------------
    assigned_filter = request.GET.get("assigned", "").strip()

    if assigned_filter == "unassigned":
        leads = leads.filter(assigned_to__isnull=True)

    elif assigned_filter.isdigit():
        leads = leads.filter(assigned_to_id=int(assigned_filter))

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------
    leads = leads.order_by("-created_at")

    # ---------------------------------------------------------
    # Dashboard statistics
    # ---------------------------------------------------------
    total_leads = CorporateLead.objects.count()

    status_counts = {
        status_code: CorporateLead.objects.filter(
            status=status_code
        ).count()
        for status_code, status_name in CorporateLead.STATUS_CHOICES
    }

    new_leads = status_counts.get("new", 0)

    # Leads created today
    today = timezone.localdate()

    leads_today = CorporateLead.objects.filter(
        created_at__date=today
    ).count()

    # Open leads
    open_leads = CorporateLead.objects.exclude(
        status__in=["won", "lost"]
    ).count()

    # Won leads
    won_leads = status_counts.get("won", 0)

    # Unassigned leads
    unassigned_leads = CorporateLead.objects.filter(
        assigned_to__isnull=True
    ).count()

    # ---------------------------------------------------------
    # Staff list
    #
    # Only active staff/admin users can be assigned to
    # Corporate Leads. Customer users are excluded.
    # ---------------------------------------------------------
    staff_users = User.objects.filter(
        is_staff=True,
        is_active=True,
    ).order_by(
        "first_name",
        "last_name",
        "username",
    )

    context = {
        "leads": leads,

        # Search/filter values
        "search_query": search_query,
        "status_filter": status_filter,
        "lead_type_filter": lead_type_filter,
        "assigned_filter": assigned_filter,

        # Main statistics
        "total_leads": total_leads,
        "new_leads": new_leads,
        "leads_today": leads_today,
        "open_leads": open_leads,
        "won_leads": won_leads,
        "unassigned_leads": unassigned_leads,

        # Individual status counts
        "status_counts": status_counts,

        # Choices for filters
        "status_choices": CorporateLead.STATUS_CHOICES,
        "lead_type_choices": CorporateLead.LEAD_TYPE_CHOICES,

        # Staff
        "staff_users": staff_users,
    }

    return render(
        request,
        "dashboard/corporate_leads/list.html",
        context,
    )


@login_required
def corporate_lead_detail(request, lead_id):
    """
    Display the complete details of one CorporateLead.
    """

    lead = get_object_or_404(
        CorporateLead.objects.select_related("assigned_to"),
        pk=lead_id,
    )

    # ---------------------------------------------------------
    # Staff list
    #
    # Only active staff/admin users are available for
    # Corporate Lead assignment.
    # ---------------------------------------------------------
    staff_users = User.objects.filter(
        is_staff=True,
        is_active=True,
    ).order_by(
        "first_name",
        "last_name",
        "username",
    )

    context = {
        "lead": lead,
        "staff_users": staff_users,
        "status_choices": CorporateLead.STATUS_CHOICES,
        "lead_type_choices": CorporateLead.LEAD_TYPE_CHOICES,
    }

    return render(
        request,
        "dashboard/corporate_leads/detail.html",
        context,
    )


@login_required
def corporate_lead_update(request, lead_id):
    """
    Update CorporateLead status, assignment, internal notes
    and follow-up date.

    This intentionally does not modify the original customer
    submission fields.

    Only active staff/admin users can be assigned to a
    CorporateLead.
    """

    lead = get_object_or_404(
        CorporateLead,
        pk=lead_id,
    )

    if request.method != "POST":
        return redirect(
            "corporate_lead_detail",
            lead_id=lead.id,
        )

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------
    new_status = request.POST.get("status", "").strip()

    valid_statuses = {
        choice[0]
        for choice in CorporateLead.STATUS_CHOICES
    }

    if new_status in valid_statuses:
        lead.status = new_status

    # ---------------------------------------------------------
    # Staff assignment
    # ---------------------------------------------------------
    assigned_to_value = request.POST.get(
        "assigned_to",
        "",
    ).strip()

    if assigned_to_value:
        try:
            assigned_user = User.objects.get(
                pk=int(assigned_to_value),
                is_staff=True,
                is_active=True,
            )

            lead.assigned_to = assigned_user

        except (
            User.DoesNotExist,
            ValueError,
            TypeError,
        ):
            lead.assigned_to = None

    else:
        lead.assigned_to = None

    # ---------------------------------------------------------
    # Internal notes
    # ---------------------------------------------------------
    lead.internal_notes = request.POST.get(
        "internal_notes",
        "",
    ).strip()

    # ---------------------------------------------------------
    # Follow-up date
    # ---------------------------------------------------------
    follow_up_date = request.POST.get(
        "follow_up_date",
        "",
    ).strip()

    if follow_up_date:
        try:
            from datetime import datetime

            lead.follow_up_date = datetime.strptime(
                follow_up_date,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            messages.error(
                request,
                "The follow-up date is not valid.",
            )

            return redirect(
                "corporate_lead_detail",
                lead_id=lead.id,
            )

    else:
        lead.follow_up_date = None

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------
    lead.save()

    messages.success(
        request,
        f"Corporate lead #{lead.id} has been updated successfully.",
    )

    return redirect(
        "corporate_lead_detail",
        lead_id=lead.id,
    )