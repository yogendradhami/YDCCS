from functools import wraps

from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """
    Require an authenticated staff member or superuser.

    Use this for dashboard views that expose or modify
    business/admin data.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper