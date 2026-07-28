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

        if request.path in {"/robots.txt", "/sitemap.xml"}:
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
            response["X-Robots-Tag"] = (
                "noindex, nofollow"
            )
            response["Cache-Control"] = (
                "private, no-store"
            )

        elif (
            response.status_code == 200
            and "text/html" in response.get(
                "Content-Type", ""
            )
        ):
            response["X-Robots-Tag"] = (
                "index, follow"
            )

        return response


class CacheHeaderMiddleware:
    """
    Set cache headers safely:
    - SEO files cached
    - Static/media cached
    - Public pages cached
    - Private pages never cached
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        # Never cache authenticated users
        if request.user.is_authenticated:
            response["Cache-Control"] = (
                "private, no-store"
            )
            return response

        path = request.path

        # Never cache private areas
        private_paths = (
            "/admin/",
            "/dashboard/",
            "/portal/",
            "/employee/",
            "/booking/",
            "/checkout/",
            "/account/",
            "/login/",
            "/register/",
            "/password-reset/",
        )

        if path.startswith(private_paths):
            response["Cache-Control"] = (
                "private, no-store"
            )
            return response


        # SEO files
        if path == "/robots.txt":
            response["Cache-Control"] = (
                "public, max-age=86400"
            )

        elif path == "/sitemap.xml":
            response["Cache-Control"] = (
                "public, max-age=86400"
            )


        # Static files
        elif path.startswith("/static/"):
            response["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )


        # Media files
        elif path.startswith("/media/"):
            response["Cache-Control"] = (
                "public, max-age=2592000"
            )


        # Public website pages
        elif response.status_code == 200:
            response["Cache-Control"] = (
                "public, max-age=3600, must-revalidate"
            )


        return response