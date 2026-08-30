from django.urls import path

from . import views


app_name = "analytics"


urlpatterns = [
    path(
        "track/",
        views.track_event,
        name="track_event",
    ),

    path(
        "track/search/",
        views.track_search,
        name="track_search",
    ),

    path(
        "dashboard/",
        views.analytics_dashboard,
        name="dashboard",
    ),
]