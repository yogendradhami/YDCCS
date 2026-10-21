# core/middleware.py

import logging
import time

from django.contrib import messages
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import connection
from django.http import Http404
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


DASHBOARD_PERMISSION_SECTIONS = {
    "/dashboard/users/": "security.manage_users",
    "/dashboard/security/": "security.view_security_center",
    "/dashboard/leads/": (("quotes", "quoterequest"),),
    "/dashboard/quote-requests/": (("quotes", "quoterequest"),),
    "/dashboard/quote-followups/": (("quotes", "quoterequest"),),
    "/dashboard/quote-conversion-analytics/": (("quotes", "quoterequest"),),
    "/dashboard/ai-quote-estimator/": (("quotes", "quoterequest"),),
    "/dashboard/corporate-leads/": (("corporate", "corporatelead"),),
    "/dashboard/customers/": (("customers", "customer"),),
    "/dashboard/customer-": (("customers", "customer"),),
    "/dashboard/bookings/": (("bookings", "booking"),),
    "/dashboard/calendar/": (("bookings", "booking"),),
    "/dashboard/contracts/": (("contracts", "cleaningcontract"),),
    "/dashboard/reports/": (("reports", "cleaningreport"),),
    "/dashboard/gallery/": (("gallery", "galleryitem"),),
    "/dashboard/reviews/": (("reviews", "review"),),
    "/dashboard/review-": (("reviews", "review"),),
    "/dashboard/employee-": (("employees", "employee"),),
    "/dashboard/employees/": (("employees", "employee"),),
    "/dashboard/induction/": (("induction", "employeeinduction"),),
    "/dashboard/attendance/": (("attendance", "attendancelog"),),
    "/dashboard/leave/": (("leave_management", "leaverequest"),),
    "/dashboard/rosters/": (("rosters", "roster"),),
    "/dashboard/payroll/": (("payroll", "payrollrecord"),),
    "/dashboard/invoices/": (("invoices", "invoice"),),
    "/dashboard/expenses/": (("expenses", "expense"),),
    "/dashboard/careers/": (("dashboard", "careerapplication"),),
    "/dashboard/campaign-": (("dashboard", "campaignlog"),),
    "/dashboard/vip-campaigns/": (("dashboard", "campaignlog"),),
    "/dashboard/email-": (("dashboard", "emaillog"),),
    "/dashboard/settings/": (("dashboard", "companysettings"),),
    "/dashboard/activity/": (("dashboard", "activitylog"),),
    "/dashboard/equipment/": (("dashboard", "equipment"),),
    "/dashboard/maintenance/": (("dashboard", "maintenancehistory"),),
    "/dashboard/supplies/": (("dashboard", "cleaningsupply"),),
    "/dashboard/purchase-orders/": (("dashboard", "purchaseorder"),),
    "/dashboard/suppliers/": (("dashboard", "supplier"),),
    "/dashboard/vehicles/": (("dashboard", "vehicle"),),
    "/dashboard/faq-questions/": (("core", "faqquestion"),),
    "/dashboard/support/": (("support", "chatenquiry"),),
    "/dashboard/financials/": (
        ("invoices", "invoice"),
        ("expenses", "expense"),
        ("payroll", "payrollrecord"),
    ),
    "/dashboard/finance-": (
        ("invoices", "invoice"),
        ("expenses", "expense"),
        ("payroll", "payrollrecord"),
    ),
    "/dashboard/gst-report/": (("invoices", "invoice"),),
    "/dashboard/profit-loss/": (("invoices", "invoice"), ("expenses", "expense")),
    "/dashboard/business-": (("dashboard", "activitylog"),),
    "/dashboard/executive-": (("dashboard", "activitylog"),),
    "/dashboard/operations-centre/": (("bookings", "booking"),),
    "/dashboard/service-performance/": (("bookings", "booking"),),
    "/dashboard/job-profitability/": (("invoices", "invoice"),),
    "/dashboard/performance/": (("employees", "employee"),),
    "/dashboard/owner-": (("dashboard", "activitylog"),),
    "/dashboard/reminders/": (("invoices", "invoice"),),
    "/dashboard/": "security.view_security_center",
}


def dashboard_required_permissions(path, method):
    section = next(
        (
            permissions
            for prefix, permissions in DASHBOARD_PERMISSION_SECTIONS.items()
            if path.startswith(prefix)
        ),
        None,
    )
    if section is None:
        return None
    if isinstance(section, str):
        return (section,)
    if not section:
        return ()
    if len(section) == 2 and isinstance(section[0], str):
        section = (section,)

    lowered_path = path.casefold()
    if any(part in lowered_path for part in ("/delete", "/remove")):
        action = "delete"
    elif any(part in lowered_path for part in ("/add", "/create")):
        action = "add"
    elif any(part in lowered_path for part in ("/edit", "/update", "/approve", "/mark-", "/send")):
        action = "change"
    elif method == "POST":
        action = "change"
    else:
        action = "view"
    return tuple(f"{app_label}.{action}_{model_name}" for app_label, model_name in section)


class ExceptionLoggingMiddleware:
    """Write unexpected request tracebacks to the service console logs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, (Http404, PermissionDenied, SuspiciousOperation)):
            logger.error(
                "Unhandled request exception for %s %s",
                request.method,
                request.path,
                exc_info=(type(exception), exception, exception.__traceback__),
            )
        return None


class SlowRequestLoggingMiddleware:
    """Record end-to-end and SQL timing for slow HTTP requests."""

    SLOW_REQUEST_SECONDS = 1.0

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        query_stats = {"count": 0, "seconds": 0.0}

        def time_query(execute, sql, params, many, context):
            query_started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                query_stats["count"] += 1
                query_stats["seconds"] += time.perf_counter() - query_started

        response = None
        try:
            with connection.execute_wrapper(time_query):
                response = self.get_response(request)
            return response
        finally:
            elapsed = time.perf_counter() - started
            if elapsed >= self.SLOW_REQUEST_SECONDS:
                logger.warning(
                    "Slow request method=%s path=%s status=%s total_ms=%.1f db_queries=%s db_ms=%.1f",
                    request.method,
                    request.path,
                    getattr(response, "status_code", "exception"),
                    elapsed * 1000,
                    query_stats["count"],
                    query_stats["seconds"] * 1000,
                )


class RoleAccessMiddleware:
    """
    Role-based access control.

    Rules:
    - Customers can access /portal/ only.
    - Employees can access /employee/ only.
    - Staff and superusers can access all protected areas.
    - OAuth callbacks that must be reached before authentication
      are explicitly allowed through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # ======================================================
        # PUBLIC / AUTHENTICATION PATHS
        # ======================================================
        #
        # These paths must be reachable without an authenticated
        # user. This includes OAuth callbacks because the external
        # provider redirects the browser back before Django has
        # established the application session.
        #

        public_paths = (
            # Static / media
            "/static/",
            "/media/",

            # Customer authentication
            "/portal/login/",
            "/portal/register/",
            "/portal/verify-email/",
            "/portal/resend-verification/",
            "/portal/logout/",
            "/portal/password-reset/",

            # Employee authentication
            "/employee/login/",
            "/employee/logout/",

            # Employee Google OAuth callback
            "/employee/google/oauth/callback/",

            # Dashboard authentication
            "/dashboard/login/",
            "/dashboard/logout/",
        )

        if path.startswith(public_paths):
            return self.get_response(request)

        # ======================================================
        # UNAUTHENTICATED USERS
        # ======================================================

        if not request.user.is_authenticated:

            if path.startswith("/dashboard/"):
                return redirect("dashboard_login")

            if path.startswith("/employee/"):
                return redirect("employee_login")

            if path.startswith("/portal/"):
                return redirect("portal_login")

            return self.get_response(request)

        # ======================================================
        # STAFF / SUPERUSER
        # ======================================================
        #
        # Staff users need a dashboard role. Superusers retain full access.
        #

        if request.user.is_staff or request.user.is_superuser:
            if request.user.is_superuser or not path.startswith("/dashboard/"):
                return self.get_response(request)

            if path.startswith("/dashboard/logout/"):
                return self.get_response(request)

            if not request.user.has_perm("security.access_dashboard"):
                raise PermissionDenied

            required_permissions = dashboard_required_permissions(
                path,
                request.method,
            )
            if required_permissions is None:
                raise PermissionDenied
            if required_permissions and not any(
                request.user.has_perm(permission)
                for permission in required_permissions
            ):
                raise PermissionDenied
            return self.get_response(request)

        # ======================================================
        # DETERMINE USER ROLE
        # ======================================================

        is_customer = hasattr(
            request.user,
            "customer_profile",
        )

        is_employee = hasattr(
            request.user,
            "employee_profile",
        )

        # ======================================================
        # DASHBOARD ACCESS
        # ======================================================

        if path.startswith("/dashboard/"):
            messages.error(
                request,
                "You do not have permission to access admin dashboard.",
            )

            if is_customer:
                return redirect("portal_dashboard")

            if is_employee:
                return redirect("employee_dashboard")

            return redirect("/")

        # ======================================================
        # EMPLOYEE PORTAL ACCESS
        # ======================================================

        if path.startswith("/employee/") and not is_employee:
            messages.error(
                request,
                "Only employees can access employee portal.",
            )

            if is_customer:
                return redirect("portal_dashboard")

            return redirect("/")

        # ======================================================
        # CUSTOMER PORTAL ACCESS
        # ======================================================

        if path.startswith("/portal/") and not is_customer:
            messages.error(
                request,
                "Only customers can access customer portal.",
            )

            if is_employee:
                return redirect("employee_dashboard")

            return redirect("/")

        return self.get_response(request)


class SEOMiddleware:
    """
    Controls SEO-related response headers.

    Public HTML pages:
        X-Robots-Tag: index, follow

    Private application areas:
        X-Robots-Tag: noindex, nofollow

    Authenticated responses:
        Cache-Control: private, no-store

    Sitemap and robots.txt are handled separately.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ======================================================
        # SITEMAP
        # ======================================================

        if request.path == "/sitemap.xml":
            # Django may add an X-Robots-Tag header to the
            # sitemap. Remove it so the sitemap itself remains
            # crawlable.
            if "X-Robots-Tag" in response.headers:
                del response.headers["X-Robots-Tag"]

            return response

        # ======================================================
        # ROBOTS.TXT
        # ======================================================

        if request.path == "/robots.txt":
            return response

        # ======================================================
        # AUTHENTICATED RESPONSES
        # ======================================================

        if request.user.is_authenticated:
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # PRIVATE APPLICATION AREAS
        # ======================================================

        private_paths = (
            "/admin/",
            "/dashboard/",
            "/portal/",
            "/employee/",
        )

        if request.path.startswith(private_paths):
            response["X-Robots-Tag"] = "noindex, nofollow"
            response["Cache-Control"] = "private, no-store"

        # ======================================================
        # PUBLIC HTML
        # ======================================================

        elif (
            response.status_code == 200
            and "text/html" in response.get("Content-Type", "")
        ):
            response["X-Robots-Tag"] = "index, follow"

        return response


class CacheHeaderMiddleware:
    """
    Safe cache-control policy.

    Goals:
    - Keep caching for public website pages.
    - Keep long-lived caching for static files.
    - Keep media caching.
    - Cache robots.txt and sitemap.xml.
    - Never publicly cache authenticated responses.
    - Never cache state-changing requests.
    - Avoid caching requests carrying session/CSRF cookies.
    - Protect sensitive application areas from accidental caching.

    This middleware does not modify:
    - application logic
    - authentication
    - SEO behaviour
    - URLs
    - templates
    - database access
    - Cloudinary
    - Stripe
    - email
    - OAuth configuration
    - Channels
    - WebSockets
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path

        # ======================================================
        # 1. NEVER CACHE STATE-CHANGING REQUESTS
        # ======================================================

        if request.method not in ("GET", "HEAD"):
            response["Cache-Control"] = "no-store"
            return response

        # ======================================================
        # 2. NEVER CACHE AUTHENTICATED USERS
        # ======================================================

        if request.user.is_authenticated:
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 3. NEVER CACHE REQUESTS WITH SESSION / CSRF COOKIES
        # ======================================================

        if (
            "sessionid" in request.COOKIES
            or "csrftoken" in request.COOKIES
        ):
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 4. NEVER CACHE RESPONSES THAT SET COOKIES
        # ======================================================

        if "Set-Cookie" in response.headers:
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 5. PRIVATE / SENSITIVE APPLICATION AREAS
        # ======================================================

        private_paths = (
            # Django admin
            "/admin/",

            # Internal dashboards
            "/dashboard/",

            # Customer portal
            "/portal/",

            # Employee portal
            "/employee/",

            # Authentication
            "/login/",
            "/logout/",
            "/register/",
            "/password-reset/",

            # Booking / checkout / account
            "/booking/",
            "/bookings/",
            "/checkout/",
            "/account/",

            # Customer information
            "/customers/",
            "/customer/",

            # Financial information
            "/invoice/",
            "/invoices/",
            "/payroll/",
            "/expenses/",

            # Employee information
            "/employees/",
            "/attendance/",
            "/leave/",
            "/leave_management/",
            "/rosters/",

            # Business management
            "/contracts/",
            "/reports/",

            # Notifications
            "/notifications/",

            # Support / live chat
            "/support/",
            "/chat/",

            # Analytics
            "/analytics/",
        )

        if path.startswith(private_paths):
            response["Cache-Control"] = "private, no-store"
            return response

        # ======================================================
        # 6. SEO FILES
        # ======================================================

        if path == "/robots.txt":
            response["Cache-Control"] = (
                "public, max-age=86400"
            )
            return response

        if path == "/sitemap.xml":
            response["Cache-Control"] = (
                "public, max-age=86400"
            )
            return response

        # ======================================================
        # 7. STATIC FILES
        # ======================================================

        if path.startswith("/static/"):
            response["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )
            return response

        # ======================================================
        # 8. MEDIA FILES
        # ======================================================

        if path.startswith("/media/"):
            response["Cache-Control"] = (
                "public, max-age=2592000"
            )
            return response

        # ======================================================
        # 9. SAFE PUBLIC WEBSITE PAGES
        # ======================================================
        #
        # Only normal anonymous GET/HEAD requests reach here.
        #

        if (
            response.status_code == 200
            and "text/html" in response.get(
                "Content-Type",
                "",
            )
        ):
            response["Cache-Control"] = (
                "public, max-age=3600, must-revalidate"
            )

        return response
