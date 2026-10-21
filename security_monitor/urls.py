
from django.urls import path

from . import views

app_name = "security_monitor"

urlpatterns = [
    path("", views.security_dashboard, name="dashboard"),
    path(
        "findings/<int:pk>/update/",
        views.update_finding,
        name="update_finding",
    ),
    path("audit/run/", views.run_security_audit, name="run_audit"),
]
