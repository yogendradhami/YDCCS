from django.urls import path

from .views import (
    mark_notification_area_read,
    mark_notifications_read,
    notification_status,
)

urlpatterns = [
    path(
        "notifications/mark-read/",
        mark_notifications_read,
        name="mark_notifications_read",
    ),
    path(
        "notifications/mark-area-read/<slug:area>/",
        mark_notification_area_read,
        name="mark_notification_area_read",
    ),
    path(
        "notifications/status/",
        notification_status,
        name="notification_status",
    ),
]
