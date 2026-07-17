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
            "/admin/",
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
    """Add lightweight SEO headers for public and private pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")

        if request.path.startswith("/admin/") or request.path.startswith("/dashboard/") or request.path.startswith("/portal/") or request.path.startswith("/employee/"):
            response["X-Robots-Tag"] = "noindex, nofollow"
        elif "text/html" in content_type:
            response.setdefault("X-Robots-Tag", "index, follow")

        return response


class CacheHeaderMiddleware:
    """Set Cache-Control headers for static assets and HTML pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Static assets: cache for 1 year (immutable hashed files)
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        
        # Media files: cache for 30 days
        elif request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=2592000'
        
        # HTML pages: no-cache but revalidate
        elif request.path.startswith('/') and not request.path.startswith('/admin/'):
            response['Cache-Control'] = 'public, max-age=3600, must-revalidate'
        
        return response