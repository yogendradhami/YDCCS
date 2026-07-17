from django import forms
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import SupportTicket


class SupportTicketForm(forms.ModelForm):

    class Meta:
        model = SupportTicket

        fields = [
            "subject",
            "message",
            "priority",
        ]

        widgets = {
<<<<<<< HEAD
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }
=======
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),
        }
>>>>>>> 5815f15 (Initial project commit)
