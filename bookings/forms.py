from django import forms

from leave_management.models import LeaveRequest

from .models import Booking, JobPhoto
from .services import get_booking_service_choices
from leave_management.models import LeaveRequest

from .models import Booking, JobPhoto


class BookingServiceChoicesValidationMixin:
    def _get_validation_exclusions(self):
        exclude = super()._get_validation_exclusions()
        # The form field validates against the live service catalog; the model
        # field's legacy choices would reject catalog services after form validation.
        exclude.add("service_type")
        return exclude



class BookingForm(BookingServiceChoicesValidationMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        service_choices = get_booking_service_choices()
        if self.instance and self.instance.pk:
            current_service = self.instance.service_type
            if current_service and current_service not in dict(service_choices):
                service_choices.append((current_service, current_service))
        self.fields["service_type"].choices = service_choices

        self.fields["customer"].required = False
        self.fields["customer"].label = "Customer (Optional)"
        self.fields["customer"].empty_label = "No customer"
        self.fields["assigned_employee"].required = False
        self.fields["assigned_employee"].label = "Assigned Employee (Optional)"
        self.fields["assigned_employee"].empty_label = "No employee assigned"
        self.fields["assigned_employee"].queryset = (
            self.fields["assigned_employee"].queryset.filter(active=True)
        )

    class Meta:
        model = Booking

        fields = [
            "customer",
            "service_type",
            "booking_date",
            "booking_time",
            "address",
            "suburb_postcode",
            "quoted_price",
            "assigned_employee",
            "status",
            "notes",
        ]

        widgets = {
            "customer": forms.Select(attrs={"class": "form-control"}),
            "service_type": forms.Select(attrs={"class": "form-control"}),
            "booking_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "booking_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Full job address",
                }
            ),
            "suburb_postcode": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Prospect 5082",
                }
            ),
            "quoted_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 150",
                    "step": "0.01",
                }
            ),
            "assigned_employee": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Booking notes",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        booking_date = cleaned_data.get("booking_date")
        assigned_employee = cleaned_data.get("assigned_employee")

        if booking_date and assigned_employee:

            approved_leave = LeaveRequest.objects.filter(
                employee=assigned_employee,
                status="approved",
                start_date__lte=booking_date,
                end_date__gte=booking_date,
            ).first()

            if approved_leave:
                raise forms.ValidationError(
                    f"{assigned_employee.full_name} is on approved "
                    f"{approved_leave.get_leave_type_display()} "
                    f"from {approved_leave.start_date} "
                    f"to {approved_leave.end_date}."
                )

            booking_time = cleaned_data.get("booking_time")

            if booking_time:
                existing_booking = (
                    Booking.objects.filter(
                        assigned_employee=assigned_employee,
                        booking_date=booking_date,
                        booking_time=booking_time,
                    )
                    .exclude(id=self.instance.id)
                    .exclude(status="cancelled")
                    .first()
                )

                if existing_booking:
                    raise forms.ValidationError(
                        f"{assigned_employee.full_name} already has another booking "
                        f"on {booking_date} at {booking_time}."
                    )

        return cleaned_data

class PublicBookingForm(BookingServiceChoicesValidationMixin, forms.ModelForm):
    name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    workflow_key = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.idempotency_key = kwargs.pop("idempotency_key", None)
        super().__init__(*args, **kwargs)
        self.fields["service_type"].choices = get_booking_service_choices()

    class Meta:
        model = Booking
        fields = [
            "name",
            "email",
            "phone",
            "service_type",
            "booking_date",
            "booking_time",
            "address",
            "suburb_postcode",
            "notes",
        ]

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get("booking_date")
        booking_time = cleaned_data.get("booking_time")
        if booking_date and booking_time and not (
            self.idempotency_key
            and Booking.objects.filter(
                idempotency_key=self.idempotency_key
            ).exists()
        ):
            conflict = Booking.objects.filter(
                booking_date=booking_date,
                booking_time=booking_time,
            ).exclude(status="cancelled").exists()
            if conflict:
                raise forms.ValidationError("That booking time is not available.")
        return cleaned_data


class JobPhotoForm(forms.ModelForm):

    employee_signature = forms.ImageField(required=False)

    customer_signature = forms.ImageField(required=False)

    class Meta:
        model = JobPhoto

        fields = [
            "photo_type",
            "employee_signature",
            "customer_signature",
            "notes",
        ]

        widgets = {
            "photo_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional photo notes",
                }
            ),
        }
