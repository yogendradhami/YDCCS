from django.urls import path

from . import views
from cleaning_game.dashboard import (
    cleaning_game_analytics,
)


app_name = "cleaning_game"


urlpatterns = [
    path(
        "",
        views.challenge,
        name="challenge",
    ),

    path(
        "calculate-result/",
        views.calculate_result,
        name="calculate_result",
    ),

    path(
        "track-event/",
        views.track_event,
        name="track_event",
    ),

    path(
        "dashboard/cleaning-game-analytics/",
        cleaning_game_analytics,
        name="cleaning_game_analytics",
    ),

    
]