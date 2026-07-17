# ====================================================
# YD Commercial Cleaning Services
# File: employees/forms.py
# Purpose:
# - Dashboard employee form
# - Employee portal login form
# - Employee job status form
# ====================================================

from django import forms
from django.contrib.auth.forms import AuthenticationForm

<<<<<<< HEAD
from bookings.models import Booking

from .models import Employee
=======
from .models import Employee
from bookings.models import Booking
>>>>>>> 5815f15 (Initial project commit)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee

        fields = [
            "user",
            "full_name",
            "phone",
            "email",
            "address",
            "role",
            "availability",
            "hourly_rate",
            "jobs_completed",
            "notes",
            "active",
        ]

        widgets = {
<<<<<<< HEAD
            "user": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Employee full name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Address",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "availability": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "hourly_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "jobs_completed": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
=======
            "user": forms.Select(attrs={
                "class": "form-control",
            }),

            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Employee full name",
            }),

            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Phone number",
            }),

            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email address",
            }),

            "address": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Address",
            }),

            "role": forms.Select(attrs={
                "class": "form-control",
            }),

            "availability": forms.Select(attrs={
                "class": "form-control",
            }),

            "hourly_rate": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
            }),

            "jobs_completed": forms.NumberInput(attrs={
                "class": "form-control",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
            }),

            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
>>>>>>> 5815f15 (Initial project commit)
        }


class EmployeeLoginForm(AuthenticationForm):
    username = forms.CharField(
<<<<<<< HEAD
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Employee email or username",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
            }
        )
=======
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Employee email or username",
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password",
        })
>>>>>>> 5815f15 (Initial project commit)
    )


class EmployeeJobStatusForm(forms.ModelForm):
    class Meta:
        model = Booking

        fields = [
            "status",
            "notes",
        ]

        widgets = {
<<<<<<< HEAD
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Add job update notes",
                }
            ),
        }
=======
            "status": forms.Select(attrs={
                "class": "form-control",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Add job update notes",
            }),
        }
>>>>>>> 5815f15 (Initial project commit)
