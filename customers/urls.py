from django.urls import path

<<<<<<< HEAD
from .views import booking_detail

urlpatterns = [
    path(
        "portal/bookings/<int:booking_id>/",
        booking_detail,
        name="portal_booking_detail",
    ),
]
=======
from .views import (
    portal_login,
    portal_logout,
    portal_dashboard,
    portal_bookings,
    portal_invoices,
    portal_invoice_detail,
    booking_detail,
)

urlpatterns = [
    

    path(
    "portal/bookings/<int:booking_id>/",
    booking_detail,
    name="portal_booking_detail"
),
]
>>>>>>> 5815f15 (Initial project commit)
