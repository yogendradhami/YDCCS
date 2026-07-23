from django.core.exceptions import PermissionDenied
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

        if not (
            request.user.is_superuser
            or request.user.is_staff
        ):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper
