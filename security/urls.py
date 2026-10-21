from django.urls import path
from django.views.decorators.http import require_http_methods

from . import views


urlpatterns = [
    path(
        "security/email/send-code/",
        views.send_public_email_code,
        name="security_send_public_email_code",
    ),
    path(
        "security/email/verify-code/",
        views.verify_public_email_code,
        name="security_verify_public_email_code",
    ),
    path(
        "security/activate/<uidb64>/<token>/",
        require_http_methods(["GET", "POST"])(views.activate_managed_user),
        name="security_activate_user",
    ),
    path("dashboard/users/", views.user_list, name="security_user_list"),
    path("dashboard/users/create/", views.user_create, name="security_user_create"),
    path(
        "dashboard/users/<int:user_id>/edit/",
        views.user_edit,
        name="security_user_edit",
    ),
    path(
        "dashboard/users/<int:user_id>/<str:action>/",
        views.user_access_action,
        name="security_user_access_action",
    ),
    path(
        "dashboard/users/positions/",
        views.position_list,
        name="security_position_list",
    ),
    path(
        "dashboard/users/positions/create/",
        views.position_edit,
        name="security_position_create",
    ),
    path(
        "dashboard/users/positions/<int:position_id>/edit/",
        views.position_edit,
        name="security_position_edit",
    ),
    path(
        "dashboard/security/audit/",
        views.security_center,
        name="security_center",
    ),
]
