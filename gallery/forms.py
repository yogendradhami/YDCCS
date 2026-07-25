from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

from .models import GalleryItem


class HEICImageField(forms.ImageField):

    def clean(self, data, initial=None):
        file = super().clean(data, initial)

        if file and file.name.lower().endswith((".heic", ".heif")):
            image = Image.open(file)
            image = image.convert("RGB")

            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            buffer.seek(0)

            file = InMemoryUploadedFile(
                buffer,
                "ImageField",
                file.name.rsplit(".", 1)[0] + ".jpg",
                "image/jpeg",
                buffer.getbuffer().nbytes,
                None,
            )

        return file


class GalleryItemForm(forms.ModelForm):

    image = HEICImageField(required=False)
    before_image = HEICImageField(required=False)
    after_image = HEICImageField(required=False)

    class Meta:
        model = GalleryItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})