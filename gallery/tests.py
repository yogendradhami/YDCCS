from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from gallery.models import GalleryItem


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
