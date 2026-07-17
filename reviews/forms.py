from django import forms
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
<<<<<<< HEAD
            field.widget.attrs.update({"class": "form-control"})
=======
            field.widget.attrs.update({
                "class": "form-control"
            })
>>>>>>> 5815f15 (Initial project commit)
