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

MAX_GALLERY_IMAGE_SIZE = 20 * 1024 * 1024


class HEICImageField(forms.ImageField):
    """
    Normal image field with optional HEIC/HEIF -> JPEG conversion.
    """

    def clean(self, data, initial=None):
        file = super().clean(data, initial)

        if file and getattr(file, "size", 0) > MAX_GALLERY_IMAGE_SIZE:
            raise forms.ValidationError("Each gallery image must be 20 MB or smaller.")

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

            if getattr(file, "size", 0) > MAX_GALLERY_IMAGE_SIZE:
                raise forms.ValidationError(
                    f'"{getattr(file, "name", "Image")}" is larger than 20 MB.'
                )

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
    MAX_IMAGE_SIZE = MAX_GALLERY_IMAGE_SIZE
    MAX_ADDITIONAL_IMAGES = 20

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

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("image", "before_image", "after_image"):
            uploaded = cleaned_data.get(field_name)
            if uploaded and getattr(uploaded, "size", 0) > self.MAX_IMAGE_SIZE:
                self.add_error(field_name, "Each gallery image must be 20 MB or smaller.")

        additional_images = cleaned_data.get("additional_images", [])
        if len(additional_images) > self.MAX_ADDITIONAL_IMAGES:
            self.add_error(
                "additional_images",
                f"Choose no more than {self.MAX_ADDITIONAL_IMAGES} additional images at once.",
            )
        for uploaded in additional_images:
            if getattr(uploaded, "size", 0) > self.MAX_IMAGE_SIZE:
                self.add_error(
                    "additional_images",
                    "Each gallery image must be 20 MB or smaller.",
                )
                break
        return cleaned_data

