from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from gallery.models import GalleryItem
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
