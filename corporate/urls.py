from django.urls import path

from . import views


app_name = "corporate"


urlpatterns = [
    path("", views.corporate, name="home"),
    path("proposal/", views.corporate_proposal, name="proposal"),
    path("team-contact/", views.corporate_team_contact, name="team_contact"),
    path("multi-site/", views.corporate_multi_site, name="multi_site"),
    path("success/", views.corporate_success, name="success"),
]