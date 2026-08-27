from io import BytesIO

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

# Optional HEIC/HEIF support
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass

from .models import GalleryItem


class HEICImageField(forms.ImageField):
    """
    Normal image field with optional HEIC/HEIF -> JPEG conversion.
    """

    def clean(self, data, initial=None):
        file = super().clean(data, initial)

        if file and hasattr(file, "name"):
            filename = file.name.lower()

            if filename.endswith((".heic", ".heif")):
                image = Image.open(file)
                image = image.convert("RGB")

                buffer = BytesIO()
                image.save(
                    buffer,
                    format="JPEG",
                    quality=90,
                    optimize=True,
                )
                buffer.seek(0)

                new_name = file.name.rsplit(".", 1)[0] + ".jpg"

                file = InMemoryUploadedFile(
                    buffer,
                    "ImageField",
                    new_name,
                    "image/jpeg",
                    buffer.getbuffer().nbytes,
                    None,
                )

        return file


class MultipleImageInput(forms.ClearableFileInput):
    """
    Django file input that supports selecting multiple files.
    """

    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, "getlist"):
            return files.getlist(name)

        value = files.get(name)

        if value is None:
            return []

        if isinstance(value, (list, tuple)):
            return value

        return [value]


class MultipleHEICImageField(forms.FileField):
    """
    Multiple image upload field.

    Supports:
    - JPG
    - JPEG
    - PNG
    - WEBP
    - GIF
    - HEIC
    - HEIF

    HEIC/HEIF files are converted to JPEG.
    """

    widget = MultipleImageInput(
        attrs={
            "multiple": True,
            "accept": "image/*,.heic,.heif",
            "class": "form-control",
        }
    )

    def clean(self, data, initial=None):
        """
        Clean and return a list of uploaded images.
        """

        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []

        for file in data:
            if not file:
                continue

            filename = getattr(file, "name", "").lower()

            # Validate as an image first
            try:
                image = Image.open(file)
                image.verify()
            except Exception:
                raise forms.ValidationError(
                    f'"{getattr(file, "name", "Unknown file")}" is not a valid image.'
                )

            # Reset file pointer after verify()
            try:
                file.seek(0)
            except Exception:
                pass

            # Convert HEIC/HEIF to JPEG
            if filename.endswith((".heic", ".heif")):
                image = Image.open(file).convert("RGB")

                buffer = BytesIO()

                image.save(
                    buffer,
                    format="JPEG",
                    quality=90,
                    optimize=True,
                )

                buffer.seek(0)

                new_name = file.name.rsplit(".", 1)[0] + ".jpg"

                file = InMemoryUploadedFile(
                    buffer,
                    "ImageField",
                    new_name,
                    "image/jpeg",
                    buffer.getbuffer().nbytes,
                    None,
                )

            cleaned_files.append(file)

        return cleaned_files


class GalleryItemForm(forms.ModelForm):
    """
    GalleryItem admin/dashboard form.

    Existing fields:
        image
        before_image
        after_image

    New multiple upload field:
        additional_images

    The multiple files are processed by the dashboard/admin view
    and saved as individual GalleryItem records.
    """

    image = HEICImageField(required=False)

    before_image = HEICImageField(required=False)

    after_image = HEICImageField(required=False)

    additional_images = MultipleHEICImageField(
        required=False,
        label="Additional Gallery Images",
        help_text=(
            "Select multiple images at once. "
            "JPG, PNG, WEBP, HEIC and HEIF are supported."
        ),
    )

    class Meta:
        model = GalleryItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # additional_images is not a model field, so it needs
        # to be handled separately by the form.
        if "additional_images" in self.fields:
            self.fields["additional_images"].widget.attrs.update(
                {
                    "class": "form-control",
                    "multiple": True,
                    "accept": "image/*,.heic,.heif",
                }
            )

        for field_name, field in self.fields.items():
            if field_name != "additional_images":
                field.widget.attrs.setdefault(
                    "class",
                    "form-control",
                )

