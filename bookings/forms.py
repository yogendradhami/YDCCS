from django import forms

<<<<<<< HEAD
from leave_management.models import LeaveRequest

from .models import Booking, JobPhoto
=======
from .models import Booking, JobPhoto
from leave_management.models import LeaveRequest
>>>>>>> 5815f15 (Initial project commit)


class BookingForm(forms.ModelForm):
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
<<<<<<< HEAD
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
=======

            "booking_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "booking_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),

            "address": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full job address",
            }),

            "suburb_postcode": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Prospect 5082",
            }),

            "quoted_price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., 150",
                "step": "0.01",
            }),

            "assigned_employee": forms.Select(attrs={
                "class": "form-control",
            }),

            "status": forms.Select(attrs={
                "class": "form-control",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Booking notes",
            }),
>>>>>>> 5815f15 (Initial project commit)
        }

    def clean(self):
        cleaned_data = super().clean()

        booking_date = cleaned_data.get("booking_date")
        assigned_employee = cleaned_data.get("assigned_employee")

<<<<<<< HEAD
=======
            

        
>>>>>>> 5815f15 (Initial project commit)
        if booking_date and assigned_employee:

            approved_leave = LeaveRequest.objects.filter(
                employee=assigned_employee,
                status="approved",
                start_date__lte=booking_date,
<<<<<<< HEAD
                end_date__gte=booking_date,
=======
                end_date__gte=booking_date
>>>>>>> 5815f15 (Initial project commit)
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
<<<<<<< HEAD
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
=======
                existing_booking = Booking.objects.filter(
                    assigned_employee=assigned_employee,
                    booking_date=booking_date,
                    booking_time=booking_time
                ).exclude(
                    id=self.instance.id
                ).exclude(
                    status="cancelled"
                ).first()
>>>>>>> 5815f15 (Initial project commit)

                if existing_booking:
                    raise forms.ValidationError(
                        f"{assigned_employee.full_name} already has another booking "
                        f"on {booking_date} at {booking_time}."
                    )

<<<<<<< HEAD
        return cleaned_data


class JobPhotoForm(forms.ModelForm):

    employee_signature = forms.ImageField(required=False)

    customer_signature = forms.ImageField(required=False)
=======

        return cleaned_data
    
class JobPhotoForm(forms.ModelForm):

    employee_signature = forms.ImageField(
        required=False
    )

    customer_signature = forms.ImageField(
        required=False
    )
>>>>>>> 5815f15 (Initial project commit)

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
<<<<<<< HEAD
=======

>>>>>>> 5815f15 (Initial project commit)
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional photo notes",
                }
            ),
<<<<<<< HEAD
        }
=======
        }
>>>>>>> 5815f15 (Initial project commit)
