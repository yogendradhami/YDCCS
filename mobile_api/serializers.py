
from django.utils import timezone
from rest_framework import serializers

from bookings.models import Booking
from customers.models import Customer
from rosters.models import Roster


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "address",
            "suburb_postcode",
        ]
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.full_name",
        read_only=True,
    )
    assigned_employee_name = serializers.CharField(
        source="assigned_employee.full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "customer_name",
            "service_type",
            "booking_date",
            "booking_time",
            "address",
            "suburb_postcode",
            "quoted_price",
            "assigned_employee",
            "assigned_employee_name",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "customer_name",
            "quoted_price",
            "assigned_employee",
            "assigned_employee_name",
            "status",
            "created_at",
        ]

    def validate_service_type(self, value):
        valid_services = {
            choice[0] for choice in Booking.SERVICE_CHOICES
        }

        if value not in valid_services:
            raise serializers.ValidationError(
                "Please select a supported cleaning service."
            )

        return value

    def validate_booking_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError(
                "The booking date cannot be in the past."
            )

        return value

    def create(self, validated_data):
        request = self.context["request"]

        customer = Customer.objects.filter(
            user=request.user
        ).first()

        if customer is None:
            raise serializers.ValidationError(
                "Your account has no linked customer profile."
            )

        validated_data["customer"] = customer

        return super().create(validated_data)


class RosterSerializer(serializers.ModelSerializer):
    service_type = serializers.CharField(
        source="booking.service_type",
        read_only=True,
    )
    address = serializers.CharField(
        source="booking.address",
        read_only=True,
    )

    class Meta:
        model = Roster
        fields = [
            "id",
            "booking",
            "service_type",
            "address",
            "shift_date",
            "start_time",
            "end_time",
            "status",
            "notes",
        ]
        read_only_fields = fields
