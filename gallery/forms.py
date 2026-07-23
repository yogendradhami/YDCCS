from django import forms

from .models import GalleryItem


class GalleryItemForm(forms.ModelForm):
    class Meta:
        model = GalleryItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})
