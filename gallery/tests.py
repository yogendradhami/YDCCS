from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.datastructures import MultiValueDict
from PIL import Image

from gallery.forms import GalleryItemForm
from gallery.models import GalleryItem
from gallery.upload_services import save_gallery_uploads
from gallery.views import _build_gallery_groups


class GalleryItemMediaTest(TestCase):
    def test_gallery_images_collects_each_attached_file_in_one_item(self):
        item = GalleryItem.objects.create(
            title="House Cleaning Gallery",
            service_type="House Cleaning",
            source="manual",
            image=SimpleUploadedFile("image.jpg", b"image-bytes", content_type="image/jpeg"),
            before_image=SimpleUploadedFile("before.png", b"before-bytes", content_type="image/png"),
            after_image=SimpleUploadedFile("after.webp", b"after-bytes", content_type="image/webp"),
        )

        gallery_media = [media.name for media in item.gallery_images]

        self.assertEqual(len(gallery_media), 3)
        self.assertTrue(gallery_media[0].startswith("gallery/uploads/"))
        self.assertTrue(gallery_media[1].startswith("gallery/before/"))
        self.assertTrue(gallery_media[2].startswith("gallery/after/"))

    def test_gallery_groups_expose_preview_images_for_the_card(self):
        item_a = GalleryItem.objects.create(
            title="Before and after",
            service_type="Bond Cleaning",
            source="manual",
            before_image=SimpleUploadedFile("before_a.png", b"before-a", content_type="image/png"),
            after_image=SimpleUploadedFile("after_a.png", b"after-a", content_type="image/png"),
        )
        item_b = GalleryItem.objects.create(
            title="Extra images",
            service_type="Bond Cleaning",
            source="manual",
            image=SimpleUploadedFile("main_b.png", b"main-b", content_type="image/png"),
        )
        GalleryItem.objects.create(
            title="Extra additional image",
            service_type="Bond Cleaning",
            source="manual",
            image=SimpleUploadedFile("main_c.png", b"main-c", content_type="image/png"),
        )

        groups = _build_gallery_groups([item_a, item_b])

        self.assertEqual(len(groups), 2)
        self.assertTrue(groups[0]["media"])
        self.assertTrue(any(media["url"] for media in groups[0]["media"]))
        self.assertIn("primary_media", groups[0])


class GalleryUploadValidationTests(TestCase):
    @staticmethod
    def image_file(name="photo.jpg"):
        buffer = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(buffer, format="JPEG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")

    def test_gallery_rejects_more_than_twenty_additional_images(self):
        files = [self.image_file(f"photo-{index}.jpg") for index in range(21)]
        form = GalleryItemForm(
            data={"title": "Gallery", "service_type": "House Cleaning", "source": "manual"},
            files=MultiValueDict({"additional_images": files}),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("additional_images", form.errors)

    def test_gallery_upload_saves_images_and_rows_after_storage(self):
        form = GalleryItemForm(
            data={"title": "Gallery", "service_type": "House Cleaning", "source": "manual"},
            files=MultiValueDict({"additional_images": [self.image_file()]}),
        )
        self.assertTrue(form.is_valid(), form.errors)
        item = form.save(commit=False)
        storage = GalleryItem._meta.get_field("image").storage

        with patch.object(storage, "save", side_effect=lambda name, _file: name):
            save_gallery_uploads(item, {}, form.cleaned_data["additional_images"])

        self.assertEqual(GalleryItem.objects.count(), 1)
        self.assertEqual(item.additional_images.count(), 1)

    def test_gallery_database_failure_deletes_uploaded_assets(self):
        form = GalleryItemForm(
            data={"title": "Gallery", "service_type": "House Cleaning", "source": "manual"},
            files=MultiValueDict({"additional_images": [self.image_file()]}),
        )
        self.assertTrue(form.is_valid(), form.errors)
        item = form.save(commit=False)
        storage = GalleryItem._meta.get_field("image").storage

        with patch.object(storage, "save", side_effect=lambda name, _file: name):
            with patch.object(storage, "delete") as delete_storage:
                with patch.object(GalleryItem, "save", side_effect=RuntimeError("db failure")):
                    with self.assertRaises(RuntimeError):
                        save_gallery_uploads(item, {}, form.cleaned_data["additional_images"])

        delete_storage.assert_called_once()
        self.assertEqual(GalleryItem.objects.count(), 0)
