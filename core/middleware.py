# core/middleware.py

from django.contrib import messages
from django.shortcuts import redirect


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
        # Staff and superusers are allowed to access all
        # application areas.
        #

        if request.user.is_staff or request.user.is_superuser:
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