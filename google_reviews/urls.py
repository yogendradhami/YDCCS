from django.urls import path

from . import views

urlpatterns = [
    path("google/connect/", views.google_connect, name="google_connect"),
    path("google/oauth/callback/", views.google_callback, name="google_callback"),
    path("google/reviews/", views.google_reviews, name="google_reviews"),
    path(
        "google/test-calendar/", views.test_calendar_event, name="test_calendar_event"
    ),
]
