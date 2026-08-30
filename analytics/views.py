import json
import uuid
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import ActivityEvent, SearchEvent, Visitor, VisitorSession


# ==========================================================
# VISITOR / SESSION HELPERS
# ==========================================================

def get_or_create_visitor(request):
    """
    Get the anonymous visitor from the cookie.

    The cookie stores Visitor.visitor_id, which is a UUID.
    """

    visitor_cookie = request.COOKIES.get("yd_visitor_id")

    try:
        visitor_uuid = uuid.UUID(visitor_cookie) if visitor_cookie else None
    except (ValueError, AttributeError, TypeError):
        visitor_uuid = None

    visitor = None

    if visitor_uuid:
        visitor = Visitor.objects.filter(
            visitor_id=visitor_uuid
        ).first()

    if visitor is None:
        visitor = Visitor.objects.create(
            device_type=get_device_type(request),
            browser=get_browser(request),
            operating_system=get_operating_system(request),
        )

        visitor.is_returning = False
        visitor.save(update_fields=["is_returning"])

    else:
        # --------------------------------------------------
        # Populate missing technology information for
        # existing visitors when they return to the site.
        # --------------------------------------------------

        changed_fields = []

        if not visitor.device_type:
            visitor.device_type = get_device_type(request)
            changed_fields.append("device_type")

        if not visitor.browser:
            visitor.browser = get_browser(request)
            changed_fields.append("browser")

        if not visitor.operating_system:
            visitor.operating_system = get_operating_system(request)
            changed_fields.append("operating_system")

        if changed_fields:
            visitor.save(update_fields=changed_fields)

    return visitor


def get_or_create_session(request, visitor, data=None):
    """
    Get or create the visitor's current analytics session.
    """

    data = data or {}

    session_cookie = request.COOKIES.get("yd_session_id")
    session = None

    if session_cookie:
        try:
            session_uuid = uuid.UUID(session_cookie)

            session = VisitorSession.objects.filter(
                session_id=session_uuid,
                visitor=visitor,
                is_active=True,
            ).first()

        except (ValueError, AttributeError, TypeError):
            session = None

    if session is None:
        session = VisitorSession.objects.create(
            visitor=visitor,
            landing_page=str(data.get("page_url", ""))[:1000],
            referrer=request.META.get("HTTP_REFERER", "")[:1000],
            utm_source=str(data.get("utm_source", ""))[:255],
            utm_medium=str(data.get("utm_medium", ""))[:255],
            utm_campaign=str(data.get("utm_campaign", ""))[:255],
        )

        visitor.total_sessions += 1

        if visitor.total_sessions > 1:
            visitor.is_returning = True

        visitor.last_seen = timezone.now()

        visitor.save(
            update_fields=[
                "total_sessions",
                "is_returning",
                "last_seen",
            ]
        )

    else:
        session.last_activity = timezone.now()
        session.save(update_fields=["last_activity"])

        visitor.last_seen = timezone.now()
        visitor.save(update_fields=["last_seen"])

    return session


# ==========================================================
# DEVICE / BROWSER DETECTION
# ==========================================================

def get_device_type(request):
    user_agent = request.META.get(
        "HTTP_USER_AGENT",
        "",
    ).lower()

    if "tablet" in user_agent or "ipad" in user_agent:
        return "Tablet"

    if "mobile" in user_agent or "iphone" in user_agent:
        return "Mobile"

    return "Desktop"


def get_browser(request):
    user_agent = request.META.get(
        "HTTP_USER_AGENT",
        "",
    ).lower()

    if "edg/" in user_agent:
        return "Edge"

    if "firefox" in user_agent:
        return "Firefox"

    if "chrome" in user_agent:
        return "Chrome"

    if "safari" in user_agent:
        return "Safari"

    return "Other"


def get_operating_system(request):
    user_agent = request.META.get(
        "HTTP_USER_AGENT",
        "",
    ).lower()

    if "iphone" in user_agent or "ipad" in user_agent:
        return "iOS"

    if "android" in user_agent:
        return "Android"

    if "windows" in user_agent:
        return "Windows"

    if "mac os" in user_agent or "macintosh" in user_agent:
        return "macOS"

    if "linux" in user_agent:
        return "Linux"

    return "Other"


# ==========================================================
# REQUEST DATA HELPER
# ==========================================================

def get_json_data(request):
    """
    Safely read JSON request data.
    """

    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, TypeError, ValueError):
        return None

    if not isinstance(data, dict):
        return None

    return data


# ==========================================================
# TRACK EVENT
# ==========================================================

@csrf_exempt
@require_POST
def track_event(request):
    """
    Receive analytics events from the website.

    Internal analytics and Django admin pages are never tracked.
    """

    data = get_json_data(request)

    if data is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON.",
            },
            status=400,
        )

    page_url = str(
        data.get("page_url")
        or request.path
        or ""
    ).strip()

    # ------------------------------------------------------
    # Never track internal analytics/admin pages
    # ------------------------------------------------------

    if (
        "/analytics/" in page_url.lower()
        or "/admin/" in page_url.lower()
    ):
        return JsonResponse(
            {
                "success": True,
                "ignored": True,
            }
        )

    event_type = str(
        data.get(
            "event_type",
            "PAGE_VIEW",
        )
    ).strip()

    element = str(
        data.get(
            "element",
            "",
        )
    ).strip()

    metadata = data.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    # ------------------------------------------------------
    # Validate event type
    # ------------------------------------------------------

    allowed_events = {
        choice[0]
        for choice in ActivityEvent.EVENT_TYPES
    }

    if event_type not in allowed_events:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid event type.",
            },
            status=400,
        )

    # ------------------------------------------------------
    # Visitor/session
    # ------------------------------------------------------

    visitor = get_or_create_visitor(request)

    session = get_or_create_session(
        request,
        visitor,
        data,
    )

    # ------------------------------------------------------
    # Create event
    # ------------------------------------------------------

    ActivityEvent.objects.create(
        visitor=visitor,
        session=session,
        event_type=event_type,
        page_url=page_url[:1000],
        element=element[:255],
        metadata=metadata,
    )

    # ------------------------------------------------------
    # PAGE VIEW updates
    # ------------------------------------------------------

    if event_type == "PAGE_VIEW":
        visitor.total_page_views += 1
        visitor.last_seen = timezone.now()

        visitor.save(
            update_fields=[
                "total_page_views",
                "last_seen",
            ]
        )

        session.exit_page = page_url
        session.last_activity = timezone.now()

        session.save(
            update_fields=[
                "exit_page",
                "last_activity",
            ]
        )

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    response = JsonResponse(
        {
            "success": True,
            "visitor_id": str(visitor.visitor_id),
            "session_id": str(session.session_id),
        }
    )

    response.set_cookie(
        "yd_visitor_id",
        str(visitor.visitor_id),
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="Lax",
    )

    response.set_cookie(
        "yd_session_id",
        str(session.session_id),
        max_age=60 * 30,
        httponly=True,
        samesite="Lax",
    )

    return response


# ==========================================================
# SEARCH TRACKING
# ==========================================================

@csrf_exempt
@require_POST
def track_search(request):
    """
    Record a website search.
    """

    data = get_json_data(request)

    if data is None:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON.",
            },
            status=400,
        )

    page_url = str(
        data.get(
            "page_url",
            "",
        )
    ).strip()

    # ------------------------------------------------------
    # Never track searches from internal pages.
    # ------------------------------------------------------

    if (
        "/analytics/" in page_url.lower()
        or "/admin/" in page_url.lower()
    ):
        return JsonResponse(
            {
                "success": True,
                "ignored": True,
            }
        )

    query = str(
        data.get(
            "query",
            "",
        )
    ).strip()

    if not query:
        return JsonResponse(
            {
                "success": False,
                "error": "Search query is required.",
            },
            status=400,
        )

    visitor = get_or_create_visitor(request)

    session = get_or_create_session(
        request,
        visitor,
        data,
    )

    # ------------------------------------------------------
    # Save SearchEvent
    # ------------------------------------------------------

    SearchEvent.objects.create(
        visitor=visitor,
        session=session,
        query=query[:500],
        page_url=page_url[:1000],
    )

    # ------------------------------------------------------
    # Also save SEARCH ActivityEvent
    # ------------------------------------------------------

    ActivityEvent.objects.create(
        visitor=visitor,
        session=session,
        event_type="SEARCH",
        page_url=page_url[:1000],
        element="website_search",
        metadata={
            "query": query[:500],
        },
    )

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    response = JsonResponse(
        {
            "success": True,
        }
    )

    response.set_cookie(
        "yd_visitor_id",
        str(visitor.visitor_id),
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="Lax",
    )

    response.set_cookie(
        "yd_session_id",
        str(session.session_id),
        max_age=60 * 30,
        httponly=True,
        samesite="Lax",
    )

    return response


# ==========================================================
# ANALYTICS DASHBOARD
# ==========================================================

@staff_member_required
def analytics_dashboard(request):
    """
    Main YD Commercial Cleaning Services analytics dashboard.

    Supports:
        - Today
        - Last 7 days
        - Last 30 days
    """

    now = timezone.now()

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    yesterday_start = today_start - timedelta(days=1)

    seven_days_start = now - timedelta(days=7)

    thirty_days_start = now - timedelta(days=30)

    # ======================================================
    # SELECTED PERIOD
    # ======================================================

    period = request.GET.get(
        "period",
        "today",
    ).lower()

    if period not in {
        "today",
        "7days",
        "30days",
    }:
        period = "today"

    if period == "7days":
        period_start = seven_days_start
        period_label = "Last 7 Days"

    elif period == "30days":
        period_start = thirty_days_start
        period_label = "Last 30 Days"

    else:
        period = "today"
        period_start = today_start
        period_label = "Today"

    # ======================================================
    # BASE QUERYSETS
    # ======================================================

    period_events = ActivityEvent.objects.filter(
        created_at__gte=period_start,
    )

    period_page_views = period_events.filter(
        event_type="PAGE_VIEW",
    )

    period_sessions = VisitorSession.objects.filter(
        started_at__gte=period_start,
    )

    # ======================================================
    # VISITORS
    # ======================================================

    visitors_period = (
        period_events
        .values("visitor_id")
        .distinct()
        .count()
    )

    total_visitors = Visitor.objects.count()

    returning_visitors = (
        period_events
        .filter(
            visitor__is_returning=True,
        )
        .values("visitor_id")
        .distinct()
        .count()
    )

    new_visitors = Visitor.objects.filter(
        first_seen__gte=period_start,
        is_returning=False,
    ).count()

    # ======================================================
    # SESSIONS
    # ======================================================

    sessions_period = period_sessions.count()

    total_sessions = VisitorSession.objects.count()

    active_visitors = (
        VisitorSession.objects
        .filter(
            last_activity__gte=now - timedelta(minutes=5),
            is_active=True,
        )
        .values("visitor_id")
        .distinct()
        .count()
    )

    # ======================================================
    # PAGE VIEWS
    # ======================================================

    page_views_period = period_page_views.count()

    total_page_views = ActivityEvent.objects.filter(
        event_type="PAGE_VIEW",
    ).count()

    # ======================================================
    # CONVERSION EVENTS
    # ======================================================

    phone_clicks = period_events.filter(
        event_type="PHONE_CLICK",
    ).count()

    email_clicks = period_events.filter(
        event_type="EMAIL_CLICK",
    ).count()

    quote_starts = period_events.filter(
        event_type="QUOTE_START",
    ).count()

    quote_submissions = period_events.filter(
        event_type="QUOTE_SUBMIT",
    ).count()

    booking_starts = period_events.filter(
        event_type="BOOKING_START",
    ).count()

    booking_completions = period_events.filter(
        event_type="BOOKING_COMPLETE",
    ).count()

    # ======================================================
    # CONVERSION RATES
    # ======================================================

    if quote_starts:
        quote_conversion_rate = round(
            (quote_submissions / quote_starts) * 100,
            1,
        )
    else:
        quote_conversion_rate = 0

    if booking_starts:
        booking_conversion_rate = round(
            (booking_completions / booking_starts) * 100,
            1,
        )
    else:
        booking_conversion_rate = 0

    if visitors_period:
        quote_visitor_rate = round(
            (quote_submissions / visitors_period) * 100,
            1,
        )

        booking_visitor_rate = round(
            (booking_completions / visitors_period) * 100,
            1,
        )
    else:
        quote_visitor_rate = 0
        booking_visitor_rate = 0

    # ======================================================
    # POPULAR PAGES
    # ======================================================

    # Exclude internal analytics/admin URLs even if older
    # records contain full URLs rather than only paths.

    popular_pages = (
        period_page_views
        .exclude(page_url="")
        .exclude(page_url__icontains="/analytics/")
        .exclude(page_url__icontains="/admin/")
        .values("page_url")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # ======================================================
    # POPULAR CLICKS
    # ======================================================

    popular_clicks = (
        period_events
        .filter(
            event_type__in=[
                "CLICK",
                "CTA_CLICK",
                "PHONE_CLICK",
                "EMAIL_CLICK",
                "QUOTE_START",
                "BOOKING_START",
            ]
        )
        .exclude(element="")
        .values(
            "event_type",
            "element",
        )
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # ======================================================
    # POPULAR SEARCHES
    # ======================================================

    # Primary source: SearchEvent.

    search_events = (
        SearchEvent.objects
        .filter(
            created_at__gte=period_start,
        )
        .exclude(query="")
        .exclude(page_url__icontains="/analytics/")
        .exclude(page_url__icontains="/admin/")
        .values("query")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    popular_searches = list(search_events)

    # ------------------------------------------------------
    # Fallback:
    # If SearchEvent has no records, read SEARCH events from
    # ActivityEvent.metadata.
    # ------------------------------------------------------

    if not popular_searches:
        search_activity = (
            period_events
            .filter(
                event_type="SEARCH",
            )
            .exclude(
                page_url__icontains="/analytics/"
            )
            .exclude(
                page_url__icontains="/admin/"
            )
            .exclude(metadata={})
            .order_by("-created_at")
        )

        search_counts = {}

        for event in search_activity:
            metadata = event.metadata or {}

            query = str(
                metadata.get("query", "")
            ).strip()

            if not query:
                continue

            query = query[:500]

            search_counts[query] = (
                search_counts.get(query, 0) + 1
            )

        popular_searches = [
            {
                "query": query,
                "total": total,
            }
            for query, total in sorted(
                search_counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ]

    # ======================================================
    # DEVICE BREAKDOWN
    # ======================================================

    period_visitor_ids = (
        period_events
        .values_list(
            "visitor_id",
            flat=True,
        )
        .distinct()
    )

    device_breakdown_raw = (
        Visitor.objects
        .filter(
            pk__in=period_visitor_ids,
        )
        .exclude(device_type="")
        .values("device_type")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    device_total = sum(
        item["total"]
        for item in device_breakdown_raw
    )

    device_breakdown = []

    for item in device_breakdown_raw:
        percentage = (
            round(
                (item["total"] / device_total) * 100,
                1,
            )
            if device_total
            else 0
        )

        device_breakdown.append(
            {
                "device_type": item["device_type"],
                "total": item["total"],
                "percentage": percentage,
            }
        )

    # ======================================================
    # BROWSER BREAKDOWN
    # ======================================================

    browser_breakdown_raw = (
        Visitor.objects
        .filter(
            pk__in=period_visitor_ids,
        )
        .exclude(browser="")
        .values("browser")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    browser_total = sum(
        item["total"]
        for item in browser_breakdown_raw
    )

    browser_breakdown = []

    for item in browser_breakdown_raw:
        percentage = (
            round(
                (item["total"] / browser_total) * 100,
                1,
            )
            if browser_total
            else 0
        )

        browser_breakdown.append(
            {
                "browser": item["browser"],
                "total": item["total"],
                "percentage": percentage,
            }
        )

    # ======================================================
    # OPERATING SYSTEM BREAKDOWN
    # ======================================================

    operating_system_breakdown_raw = (
        Visitor.objects
        .filter(
            pk__in=period_visitor_ids,
        )
        .exclude(operating_system="")
        .values("operating_system")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    operating_system_total = sum(
        item["total"]
        for item in operating_system_breakdown_raw
    )

    operating_system_breakdown = []

    for item in operating_system_breakdown_raw:
        percentage = (
            round(
                (item["total"] / operating_system_total) * 100,
                1,
            )
            if operating_system_total
            else 0
        )

        operating_system_breakdown.append(
            {
                "operating_system": item["operating_system"],
                "total": item["total"],
                "percentage": percentage,
            }
        )

    # ======================================================
    # RECENT ACTIVITY
    # ======================================================

    recent_activity = (
        ActivityEvent.objects
        .select_related(
            "visitor",
            "session",
        )
        .exclude(
            page_url__icontains="/analytics/"
        )
        .exclude(
            page_url__icontains="/admin/"
        )
        .order_by("-created_at")[:20]
    )

    # ======================================================
    # YESTERDAY
    # ======================================================

    visitors_yesterday = (
        ActivityEvent.objects
        .filter(
            created_at__gte=yesterday_start,
            created_at__lt=today_start,
        )
        .values("visitor_id")
        .distinct()
        .count()
    )

    sessions_yesterday = VisitorSession.objects.filter(
        started_at__gte=yesterday_start,
        started_at__lt=today_start,
    ).count()

    page_views_yesterday = ActivityEvent.objects.filter(
        event_type="PAGE_VIEW",
        created_at__gte=yesterday_start,
        created_at__lt=today_start,
    ).count()

    # ======================================================
    # VISITOR CHANGE
    # ======================================================

    if visitors_yesterday:
        visitors_change = round(
            (
                (visitors_period - visitors_yesterday)
                / visitors_yesterday
            ) * 100,
            1,
        )
    else:
        visitors_change = 100 if visitors_period else 0

    # ======================================================
    # PAGES PER SESSION
    # ======================================================

    if sessions_period:
        pages_per_session = round(
            page_views_period / sessions_period,
            1,
        )
    else:
        pages_per_session = 0

    # ======================================================
    # TODAY VALUES
    # ======================================================

    today_visitors = (
        ActivityEvent.objects
        .filter(
            created_at__gte=today_start,
        )
        .values("visitor_id")
        .distinct()
        .count()
    )

    today_sessions = VisitorSession.objects.filter(
        started_at__gte=today_start,
    ).count()

    today_page_views = ActivityEvent.objects.filter(
        event_type="PAGE_VIEW",
        created_at__gte=today_start,
    ).count()

    today_phone_clicks = ActivityEvent.objects.filter(
        event_type="PHONE_CLICK",
        created_at__gte=today_start,
    ).count()

    today_email_clicks = ActivityEvent.objects.filter(
        event_type="EMAIL_CLICK",
        created_at__gte=today_start,
    ).count()

    today_quote_starts = ActivityEvent.objects.filter(
        event_type="QUOTE_START",
        created_at__gte=today_start,
    ).count()

    today_quote_submissions = ActivityEvent.objects.filter(
        event_type="QUOTE_SUBMIT",
        created_at__gte=today_start,
    ).count()

    today_booking_starts = ActivityEvent.objects.filter(
        event_type="BOOKING_START",
        created_at__gte=today_start,
    ).count()

    today_booking_completions = ActivityEvent.objects.filter(
        event_type="BOOKING_COMPLETE",
        created_at__gte=today_start,
    ).count()

    # ======================================================
    # DASHBOARD CONTEXT
    # ======================================================

    context = {
        # Reporting period
        "selected_period": period,
        "period_label": period_label,
        "period_start": period_start,

        # Visitors
        "visitors_today": (
            visitors_period
            if period == "today"
            else today_visitors
        ),
        "visitors_period": visitors_period,
        "new_visitors": new_visitors,
        "total_visitors": total_visitors,
        "returning_visitors": returning_visitors,
        "visitors_change": visitors_change,

        # Sessions
        "sessions_today": (
            sessions_period
            if period == "today"
            else today_sessions
        ),
        "sessions_period": sessions_period,
        "total_sessions": total_sessions,
        "active_visitors": active_visitors,

        # Page views
        "page_views_today": (
            page_views_period
            if period == "today"
            else today_page_views
        ),
        "page_views_period": page_views_period,
        "total_page_views": total_page_views,
        "pages_per_session": pages_per_session,

        # Today conversions
        "phone_clicks_today": (
            phone_clicks
            if period == "today"
            else today_phone_clicks
        ),
        "email_clicks_today": (
            email_clicks
            if period == "today"
            else today_email_clicks
        ),
        "quote_starts_today": (
            quote_starts
            if period == "today"
            else today_quote_starts
        ),
        "quote_submissions_today": (
            quote_submissions
            if period == "today"
            else today_quote_submissions
        ),
        "booking_starts_today": (
            booking_starts
            if period == "today"
            else today_booking_starts
        ),
        "booking_completions_today": (
            booking_completions
            if period == "today"
            else today_booking_completions
        ),

        # Period conversions
        "phone_clicks": phone_clicks,
        "email_clicks": email_clicks,

        "quote_starts": quote_starts,
        "quote_submissions": quote_submissions,
        "quote_conversion_rate": quote_conversion_rate,
        "quote_visitor_rate": quote_visitor_rate,

        "booking_starts": booking_starts,
        "booking_completions": booking_completions,
        "booking_conversion_rate": booking_conversion_rate,
        "booking_visitor_rate": booking_visitor_rate,

        # Popular content
        "popular_pages": popular_pages,
        "popular_clicks": popular_clicks,
        "popular_searches": popular_searches,

        # Technology
        "device_breakdown": device_breakdown,
        "browser_breakdown": browser_breakdown,
        "operating_system_breakdown": operating_system_breakdown,

        # Recent activity
        "recent_activity": recent_activity,

        # Comparisons
        "visitors_yesterday": visitors_yesterday,
        "sessions_yesterday": sessions_yesterday,
        "page_views_yesterday": page_views_yesterday,
    }

    return render(
        request,
        "dashboard/analytics/dashboard.html",
        context,
    )