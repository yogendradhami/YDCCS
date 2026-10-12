
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from bookings.models import Booking
from customers.models import Customer
from employees.models import Employee
from rosters.models import Roster

from .permissions import IsCompanyAdmin, IsCustomer, IsEmployee
from .serializers import (
    BookingSerializer,
    CustomerSerializer,
    RosterSerializer,
    UserSerializer,
)

User = get_user_model()


class CustomerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        full_name = str(request.data.get("full_name", "")).strip()
        phone = str(request.data.get("phone", "")).strip()
        password = request.data.get("password", "")

        if not all([email, full_name, phone, password]):
            raise ValidationError(
                "Full name, email, phone and password are required."
            )

        email = serializers.EmailField().run_validation(email)

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({
                "email": "An account with this email already exists."
            })

        try:
            password_validation.validate_password(password)
        except DjangoValidationError as exc:
            raise ValidationError({"password": list(exc.messages)})

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                )

                Customer.objects.create(
                    user=user,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                )
        except IntegrityError:
            raise ValidationError({
                "email": "An account with this email already exists."
            })

        return Response(
            {"message": "Account created. Please sign in to continue."},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        customer = Customer.objects.filter(user=user).first()
        employee = Employee.objects.filter(
            user=user,
            active=True,
        ).first()

        roles = []

        if customer:
            roles.append("customer")

        if employee:
            roles.append("employee")

        if user.is_staff:
            roles.append("staff")

        if (
            user.is_superuser
            or user.has_perm("bookings.view_booking")
        ):
            roles.append("company_admin")

        employee_data = None

        if employee:
            employee_data = {
                "id": employee.id,
                "full_name": employee.full_name,
                "role": employee.role,
            }

        return Response({
            "user": UserSerializer(user).data,
            "roles": roles,
            "customer": (
                CustomerSerializer(customer).data
                if customer else None
            ),
            "employee": employee_data,
        })


class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsCustomer,
    ]

    def get_queryset(self):
        return (
            Booking.objects
            .filter(customer__user=self.request.user)
            .select_related("customer", "assigned_employee")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key", "").strip()

        if not key or len(key) > 100:
            raise ValidationError({
                "Idempotency-Key":
                    "Provide a unique request key up to 100 characters."
            })

        existing = self.get_queryset().filter(
            idempotency_key=key
        ).first()

        if existing:
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                booking = serializer.save(idempotency_key=key)
        except IntegrityError:
            existing = self.get_queryset().filter(
                idempotency_key=key
            ).first()

            if existing:
                return Response(
                    self.get_serializer(existing).data,
                    status=status.HTTP_200_OK,
                )

            raise ValidationError(
                "The booking could not be created. Please retry "
                "with a new request key."
            )

        return Response(
            self.get_serializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class BookingDetailView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsCustomer,
    ]

    def get_queryset(self):
        return (
            Booking.objects
            .filter(customer__user=self.request.user)
            .select_related("customer", "assigned_employee")
        )


class EmployeeRosterView(generics.ListAPIView):
    serializer_class = RosterSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsEmployee,
    ]

    def get_queryset(self):
        return (
            Roster.objects
            .filter(employee__user=self.request.user)
            .select_related("employee", "booking")
            .order_by("shift_date", "start_time")
        )


class CompanySummaryView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCompanyAdmin,
    ]

    def get(self, request):
        today = timezone.localdate()

        return Response({
            "today": today.isoformat(),
            "bookings_today": Booking.objects.filter(
                booking_date=today
            ).count(),
            "pending_bookings": Booking.objects.filter(
                status="pending"
            ).count(),
            "confirmed_bookings": Booking.objects.filter(
                status="confirmed"
            ).count(),
            "active_employees": Employee.objects.filter(
                active=True
            ).count(),
        })
