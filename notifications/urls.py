from django.urls import path
<<<<<<< HEAD

from .views import mark_notifications_read

urlpatterns = [
    path(
        "notifications/mark-read/",
        mark_notifications_read,
        name="mark_notifications_read",
    ),
]
=======
from .views import mark_notifications_read


urlpatterns = [
    path("notifications/mark-read/", mark_notifications_read, name="mark_notifications_read"),
]
>>>>>>> 5815f15 (Initial project commit)
