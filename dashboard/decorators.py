from django.core.exceptions import PermissionDenied

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):

        print(
            "USER:",
            request.user.username,
            "STAFF:",
            request.user.is_staff,
            "SUPER:",
            request.user.is_superuser,
        )

        if not request.user.is_authenticated:
            raise PermissionDenied

        if not (
            request.user.is_superuser
            or request.user.is_staff
        ):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper