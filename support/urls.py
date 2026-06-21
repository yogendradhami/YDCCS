from django.urls import path

from .views import (
    create_ticket,
    customer_tickets,
    support_dashboard,
)

urlpatterns = [
    path("portal/support/", customer_tickets, name="customer_tickets"),
    path("portal/support/new/", create_ticket, name="create_ticket"),
    path("dashboard/support/", support_dashboard, name="support_dashboard"),
]
