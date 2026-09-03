# core/middleware.py

from django.shortcuts import redirect
from django.contrib import messages


class RoleAccessMiddleware:
    """
    Role security:
    - Customer can access /portal/ only
    - Employee can access /employee/ only
    - Admin/staff can access all
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        path = request.path

        public_paths = (
            "/static/",
            "/media/",
            "/portal/login/",
            "/portal/register/",
            "/portal/logout/",
            "/portal/password-reset/",
            "/employee/login/",
            "/employee/logout/",
            "/dashboard/login/",
            "/dashboard/logout/",
        )

        for public_path in public_paths:
            if path.startswith(public_path):
                return self.get_response(request)

        if not request.user.is_authenticated:

            if path.startswith("/dashboard/"):
                return redirect("dashboard_login")

            if path.startswith("/employee/"):
                return redirect("employee_login")

            if path.startswith("/portal/"):
                return redirect("portal_login")

            return self.get_response(request)

        if request.user.is_staff or request.user.is_superuser:
            return self.get_response(request)

        is_customer = hasattr(request.user, "customer_profile")
        is_employee = hasattr(request.user, "employee_profile")

        if path.startswith("/dashboard/"):
            messages.error(request, "You do not have permission to access admin dashboard.")

            if is_customer:
                return redirect("portal_dashboard")

            if is_employee:
                return redirect("employee_dashboard")

            return redirect("/")

        if path.startswith("/employee/") and not is_employee:
            messages.error(request, "Only employees can access employee portal.")

            if is_customer:
                return redirect("portal_dashboard")

            return redirect("/")

        if path.startswith("/portal/") and not is_customer:
            messages.error(request, "Only customers can access customer portal.")

            if is_employee:
                return redirect("employee_dashboard")

            return redirect("/")

        return self.get_response(request)

class SEOMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        # Remove Django sitemap noindex header
        if request.path == "/sitemap.xml":
            if "X-Robots-Tag" in response.headers:
                del response.headers["X-Robots-Tag"]

            return response

        if request.path == "/robots.txt":
            return response


        if request.user.is_authenticated:
            response["Cache-Control"] = "private, no-store"
            return response

        private_paths = (
            "/admin/",
            "/dashboard/",
            "/portal/",
            "/employee/",
        )

        if request.path.startswith(private_paths):
            response["X-Robots-Tag"] = "noindex, nofollow"
            response["Cache-Control"] = "private, no-store"

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
    - Keep existing caching for public website pages.
    - Keep long-lived caching for static files.
    - Keep media caching.
    - Keep robots.txt and sitemap.xml caching.
    - Never publicly cache authenticated/private responses.
    - Never cache state-changing requests.
    - Avoid caching requests carrying session/CSRF cookies.
    - Protect sensitive application areas from accidental caching.

    This middleware intentionally does NOT change application logic,
    authentication, SEO behaviour, URLs, templates, database access,
    Cloudinary, Stripe, email, OAuth, Channels or WebSockets.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        path = request.path

        # ======================================================
        # 1. NEVER CACHE STATE-CHANGING REQUESTS
        # ======================================================
        #
        # POST/PUT/PATCH/DELETE requests can contain customer,
        # employee, booking, payment, login or form information.
        #
        # Even if an application accidentally returns HTTP 200,
        # these responses must not become publicly cacheable.
        #

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
        #
        # Anonymous users can still have session state.
        #
        # A session cookie may contain information that makes a
        # response user-specific.
        #
        # A CSRF cookie can also indicate that the visitor is
        # interacting with a stateful form.
        #
        # Therefore these requests are treated conservatively.
        #

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
        #
        # These areas should never be publicly cached, even when
        # the current request happens to be anonymous.
        #
        # Some paths may redirect unauthenticated visitors.
        # Keeping them non-cacheable prevents sensitive redirects
        # or future personalised responses from becoming cached.
        #

        private_paths = (
            # Django/admin
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

            # Business/customer information
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
        #
        # Static assets are safe to cache aggressively because
        # they are versioned/managed by the deployment process.
        #

        if path.startswith("/static/"):
            response["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )
            return response

        # ======================================================
        # 8. MEDIA FILES
        # ======================================================
        #
        # Cloudinary-backed media is kept cacheable as before.
        #

        if path.startswith("/media/"):
            response["Cache-Control"] = (
                "public, max-age=2592000"
            )
            return response

        # ======================================================
        # 9. SAFE PUBLIC WEBSITE PAGES
        # ======================================================
        #
        # Preserve the existing one-hour public-page caching
        # behaviour for normal anonymous GET/HEAD requests.
        #
        # We only reach this point when:
        # - the request is GET/HEAD;
        # - the user is not authenticated;
        # - there is no session/CSRF cookie;
        # - the response does not set a cookie;
        # - the path is not private.
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

