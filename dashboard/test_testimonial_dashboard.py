from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import TestimonialVideo


@override_settings(
    CLOUDINARY_STORAGE={
        "CLOUD_NAME": "test-cloud",
        "API_KEY": "test-api-key",
        "API_SECRET": "test-secret-not-a-production-credential",
    }
)
class TestimonialVideoDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="testimonial-dashboard-admin",
            email="testimonial-dashboard@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

    def test_sidebar_page_and_list_use_dashboard_testimonial_management(self):
        TestimonialVideo.objects.create(
            title="Office clean testimonial",
            video="testimonial-videos/office-clean",
        )
        with patch(
            "core.storage.cloudinary.utils.cloudinary_url",
            return_value=("https://cdn.example/video.mp4", {}),
        ):
            response = self.client.get(reverse("testimonial_video_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Office clean testimonial")
        self.assertContains(response, "Add testimonial videos")
        self.assertContains(response, reverse("testimonial_video_list"))
        self.assertContains(response, "Gallery")

    def test_multiple_videos_create_separate_testimonials_from_filenames(self):
        with patch(
            "core.storage.cloudinary.uploader.upload",
            side_effect=[
                {"public_id": "testimonial-videos/admin/video-one"},
                {"public_id": "testimonial-videos/admin/video-two"},
            ],
        ) as upload:
            response = self.client.post(
                reverse("add_testimonial_videos"),
                {
                    "videos": [
                        SimpleUploadedFile("Video One.mp4", b"one", "video/mp4"),
                        SimpleUploadedFile("Video Two.webm", b"two", "video/webm"),
                    ],
                    "description": "A happy customer.",
                    "active": "on",
                },
            )

        self.assertRedirects(response, reverse("testimonial_video_list"))
        self.assertEqual(TestimonialVideo.objects.count(), 2)
        first = TestimonialVideo.objects.get(title="Video One")
        second = TestimonialVideo.objects.get(title="Video Two")
        self.assertEqual(first.video.name, "testimonial-videos/admin/video-one")
        self.assertEqual(second.video.name, "testimonial-videos/admin/video-two")
        self.assertEqual(first.description, "A happy customer.")
        self.assertTrue(first.active)
        self.assertEqual(upload.call_count, 2)

    def test_invalid_video_extension_is_rejected_without_uploading(self):
        with patch("core.storage.cloudinary.uploader.upload") as upload:
            response = self.client.post(
                reverse("add_testimonial_videos"),
                {
                    "videos": [
                        SimpleUploadedFile("not-a-video.txt", b"file", "text/plain"),
                    ],
                    "active": "on",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "supported video file")
        upload.assert_not_called()
        self.assertFalse(TestimonialVideo.objects.exists())

    def test_edit_can_replace_video_and_old_cloud_asset_is_removed(self):
        video = TestimonialVideo.objects.create(
            title="Original title",
            video="testimonial-videos/original",
        )
        with (
            patch(
                "core.storage.cloudinary.uploader.upload",
                return_value={"public_id": "testimonial-videos/replacement"},
            ) as upload,
            patch(
                "core.storage.cloudinary.uploader.destroy",
                return_value={"result": "ok"},
            ) as destroy,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                reverse("edit_testimonial_video", args=[video.pk]),
                {
                    "title": "Updated title",
                    "description": "Updated description",
                    "active": "on",
                    "replacement_video": SimpleUploadedFile(
                        "replacement.mp4",
                        b"replacement",
                        "video/mp4",
                    ),
                },
            )

        self.assertRedirects(response, reverse("testimonial_video_list"))
        video.refresh_from_db()
        self.assertEqual(video.title, "Updated title")
        self.assertEqual(video.video.name, "testimonial-videos/replacement")
        upload.assert_called_once()
        destroy.assert_called_once_with(
            "testimonial-videos/original",
            resource_type="video",
            invalidate=True,
        )

    def test_deleting_testimonial_removes_database_record_and_cloud_video(self):
        video = TestimonialVideo.objects.create(
            title="Delete me",
            video="testimonial-videos/to-delete",
        )
        with (
            patch(
                "core.storage.cloudinary.uploader.destroy",
                return_value={"result": "ok"},
            ) as destroy,
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                reverse("delete_testimonial_video", args=[video.pk])
            )

        self.assertRedirects(response, reverse("testimonial_video_list"))
        self.assertFalse(TestimonialVideo.objects.filter(pk=video.pk).exists())
        destroy.assert_called_once_with(
            "testimonial-videos/to-delete",
            resource_type="video",
            invalidate=True,
        )
