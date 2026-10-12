
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    BookingDetailView,
    BookingListCreateView,
    CompanySummaryView,
    CustomerRegistrationView,
    EmployeeRosterView,
    MeView,
)

app_name = "mobile_api"

urlpatterns = [
    path(
        "auth/register/",
        CustomerRegistrationView.as_view(),
        name="register",
    ),
    path(
        "auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("me/", MeView.as_view(), name="me"),
    path(
        "bookings/",
        BookingListCreateView.as_view(),
        name="booking_list_create",
    ),
    path(
        "bookings/<int:pk>/",
        BookingDetailView.as_view(),
        name="booking_detail",
    ),
    path(
        "employee/roster/",
        EmployeeRosterView.as_view(),
        name="employee_roster",
    ),
    path(
        "company/summary/",
        CompanySummaryView.as_view(),
        name="company_summary",
    ),
]
