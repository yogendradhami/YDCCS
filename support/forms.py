from django import forms

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
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "priority": forms.Select(attrs={"class": "form-control"}),
        }
