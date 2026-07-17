from django.urls import path
<<<<<<< HEAD

from . import views

=======
from . import views
>>>>>>> 5815f15 (Initial project commit)
urlpatterns = [
    path("google/connect/", views.google_connect, name="google_connect"),
    path("google/oauth/callback/", views.google_callback, name="google_callback"),
    path("google/reviews/", views.google_reviews, name="google_reviews"),
<<<<<<< HEAD
    path(
        "google/test-calendar/", views.test_calendar_event, name="test_calendar_event"
    ),
]
=======
    path("google/test-calendar/", views.test_calendar_event, name="test_calendar_event"),
    path("google/sync-reviews/",views.sync_google_reviews,name="sync_google_reviews"),


]
>>>>>>> 5815f15 (Initial project commit)
