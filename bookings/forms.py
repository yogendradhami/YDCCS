from django import forms
from django.forms import formset_factory

from leave_management.models import LeaveRequest
from employees.models import Employee

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


class BookingWorkOrderForm(forms.Form):
    service_type = forms.ChoiceField(label="Service / work order")
    price = forms.DecimalField(
        label="Price",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )
    DELETE = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_type"].choices = [("", "Choose a service")] + (
            get_booking_service_choices()
        )


BookingWorkOrderFormSet = formset_factory(
    BookingWorkOrderForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class BookingForm(BookingServiceChoicesValidationMixin, forms.ModelForm):
    assigned_employees = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.none(),
        required=False,
        label="Assigned Employees (Optional)",
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "booking-employee-checkbox",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is None and args:
            data = args[0]
        if data is not None and (
            "assigned_employees" not in data
            and "assigned_employee" in data
        ):
            data = data.copy()
            getlist = getattr(data, "getlist", None)
            selected = (
                getlist("assigned_employee")
                if getlist
                else [data.get("assigned_employee")]
            )
            selected = [employee_id for employee_id in selected if employee_id]
            if hasattr(data, "setlist"):
                data.setlist("assigned_employees", selected)
            else:
                data["assigned_employees"] = selected
            if args:
                args = (data, *args[1:])
            else:
                kwargs["data"] = data
        super().__init__(*args, **kwargs)

        service_choices = get_booking_service_choices()
        if self.instance and self.instance.pk:
            current_service = self.instance.service_type
            if current_service and current_service not in dict(service_choices):
                service_choices.append((current_service, current_service))
        self.fields["service_type"].choices = service_choices
        self.fields["service_type"].required = False
        self.fields["quoted_price"].required = False
        if not self.is_bound and service_choices:
            self.initial.setdefault("service_type", service_choices[0][0])
        if not self.is_bound:
            self.initial.setdefault(
                "quoted_price",
                self.instance.quoted_price if self.instance.pk else 0,
            )

        self.fields["customer"].required = False
        self.fields["customer"].label = "Customer (Optional)"
        self.fields["customer"].empty_label = "No customer"
        self.fields["assigned_employees"].queryset = Employee.objects.filter(
            active=True
        ).order_by("full_name")
        if not self.is_bound and self.instance and self.instance.pk:
            employee_ids = list(
                self.instance.assigned_employees.values_list("pk", flat=True)
            )
            if not employee_ids and self.instance.assigned_employee_id:
                employee_ids = [self.instance.assigned_employee_id]
            self.initial["assigned_employees"] = employee_ids

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
            "assigned_employees",
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
        assigned_employees = cleaned_data.get("assigned_employees", [])
        booking_time = cleaned_data.get("booking_time")

        if booking_date:
            for assigned_employee in assigned_employees:
                approved_leave = LeaveRequest.objects.filter(
                    employee=assigned_employee,
                    status="approved",
                    start_date__lte=booking_date,
                    end_date__gte=booking_date,
                ).first()

                if approved_leave:
                    self.add_error(
                        "assigned_employees",
                        f"{assigned_employee.full_name} is on approved "
                        f"{approved_leave.get_leave_type_display()} "
                        f"from {approved_leave.start_date} "
                        f"to {approved_leave.end_date}.",
                    )

                if booking_time:
                    existing_booking = (
                        Booking.objects.assigned_to(assigned_employee)
                        .filter(
                            booking_date=booking_date,
                            booking_time=booking_time,
                        )
                        .exclude(pk=self.instance.pk)
                        .exclude(status="cancelled")
                        .first()
                    )

                    if existing_booking:
                        self.add_error(
                            "assigned_employees",
                            f"{assigned_employee.full_name} already has another "
                            f"booking on {booking_date} at {booking_time}.",
                        )

        return cleaned_data

    def save(self, commit=True):
        booking = super().save(commit=False)
        assigned_employees = list(self.cleaned_data["assigned_employees"])
        booking.assigned_employee = (
            assigned_employees[0] if assigned_employees else None
        )
        if commit:
            booking.save()
            self.save_m2m()
        return booking

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
