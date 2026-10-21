
from django import forms

from .models import SecurityFinding


class SecurityFindingUpdateForm(forms.ModelForm):
    class Meta:
        model = SecurityFinding
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }
