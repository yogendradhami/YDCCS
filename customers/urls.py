from django.urls import path

from .views import booking_detail

urlpatterns = [
    path(
        "portal/bookings/<int:booking_id>/",
        booking_detail,
        name="portal_booking_detail",
    ),
]
