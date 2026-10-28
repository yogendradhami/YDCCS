import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import TestimonialVideo
from core.testimonial_uploads import (
    ALLOWED_TESTIMONIAL_VIDEO_FORMATS,
    MAX_TESTIMONIAL_VIDEO_BYTES,
    TESTIMONIAL_UPLOAD_SESSION_KEY,
    cleanup_testimonial_upload,
    verify_testimonial_upload_receipt,
)


@override_settings(
    CLOUDINARY_STORAGE={
        "CLOUD_NAME": "test-cloud",
        "API_KEY": "test-api-key",
        "API_SECRET": "test-secret-not-a-production-credential",
    }
)
class TestimonialVideoDirectUploadTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="testimonial-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)
        self.upload_url = reverse("admin:core_testimonialvideo_upload_batch")
        self.add_url = reverse("admin:core_testimonialvideo_add")

    def sign_batch(self, item_id=""):
        with patch("core.testimonial_uploads.api_sign_request", return_value="signed"):
            return self.client.post(
                self.upload_url,
                {
                    "action": "sign",
                    "item_id": str(item_id),
                },
            )

    def resource(self, public_id, *, resource_type="video", file_format="mp4", size=1024, version=1):
        return {
            "public_id": public_id,
            "resource_type": resource_type,
            "type": "upload",
            "format": file_format,
            "bytes": size,
            "version": version,
        }

    def finalize(self, nonce, public_id, *, signature="signed", version=1, resources=None):
        with (
            patch("core.testimonial_uploads.api_sign_request", return_value="signed"),
            patch(
                "core.testimonial_uploads.cloudinary_api.resources_by_ids",
                return_value={"resources": resources or [self.resource(public_id)]},
            ),
        ):
            return self.client.post(
                self.upload_url,
                {
                    "action": "finalize",
                    "nonce": nonce,
                    "item_id": "",
                    "receipt": json.dumps(
                        {
                            "public_id": public_id,
                            "version": version,
                            "signature": signature,
                        }
                    ),
                },
            )

    def test_staff_can_sign_short_lived_upload_without_exposing_secret(self):
        response = self.sign_batch()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["upload"]["max_file_bytes"], MAX_TESTIMONIAL_VIDEO_BYTES)
        self.assertEqual(payload["upload"]["overwrite"], "false")
        self.assertTrue(
            payload["upload"]["public_id"].startswith("testimonial-videos/admin/")
        )
        self.assertEqual(payload["upload"]["signature"], "signed")
        self.assertNotIn("api_secret", payload)
        self.assertNotIn("test-secret-not-a-production-credential", response.content.decode())

    def test_unauthorized_staff_and_public_users_cannot_sign(self):
        user = get_user_model().objects.create_user(
            username="no-testimonial-permission",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.sign_batch()

        self.assertEqual(response.status_code, 403)

        self.client.logout()
        response = self.client.post(self.upload_url, {"action": "sign", "item_id": ""})
        self.assertEqual(response.status_code, 302)

    def test_upload_endpoint_rejects_non_post_requests(self):
        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 405)

    def test_upload_endpoint_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)

        response = csrf_client.post(
            self.upload_url,
            {"action": "sign", "item_id": ""},
        )

        self.assertEqual(response.status_code, 403)

    def test_successful_finalize_and_admin_save_attach_without_reuploading(self):
        sign_response = self.sign_batch()
        self.assertEqual(sign_response.status_code, 200)
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]

        response = self.finalize(nonce, public_id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["finalized"])
        session_batch = self.client.session[TESTIMONIAL_UPLOAD_SESSION_KEY][nonce]
        self.assertEqual(session_batch["verified"]["public_id"], public_id)

        with patch("core.storage.cloudinary.uploader.upload") as upload:
            response = self.client.post(
                self.add_url,
                {
                    "title": "Direct testimonial",
                    "description": "A verified upload",
                    "active": "on",
                    "video_upload_nonce": nonce,
                },
            )

        self.assertEqual(response.status_code, 302)
        video = TestimonialVideo.objects.get(title="Direct testimonial")
        self.assertEqual(video.video.name, public_id)
        upload.assert_not_called()
        self.assertNotIn(nonce, self.client.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {}))

    def test_existing_server_mediated_admin_upload_remains_available(self):
        uploaded_file = SimpleUploadedFile(
            "legacy.mp4",
            b"legacy-test-video",
            content_type="video/mp4",
        )
        with patch(
            "core.storage.cloudinary.uploader.upload",
            return_value={"public_id": "testimonial-videos/legacy"},
        ) as upload:
            response = self.client.post(
                self.add_url,
                {
                    "title": "Legacy upload",
                    "description": "",
                    "active": "on",
                    "video": uploaded_file,
                    "video_upload_nonce": "",
                },
            )

        self.assertEqual(response.status_code, 302)
        video = TestimonialVideo.objects.get(title="Legacy upload")
        self.assertEqual(video.video.name, "testimonial-videos/legacy")
        upload.assert_called_once()

    def test_invalid_upload_signature_is_rejected(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]
        with patch("core.admin.cleanup_testimonial_upload", return_value=True) as cleanup:
            response = self.finalize(nonce, public_id, signature="incorrect")

        self.assertEqual(response.status_code, 400)
        cleanup.assert_called_once()

    def test_cross_batch_public_id_is_rejected(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        expected_id = sign_response.json()["upload"]["public_id"]
        with patch("core.admin.cleanup_testimonial_upload", return_value=True):
            response = self.finalize(
                nonce,
                "testimonial-videos/admin/another-batch/video",
            )

        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(expected_id, "testimonial-videos/admin/another-batch/video")

    def test_missing_duplicate_and_mismatched_receipts_are_rejected(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]
        batch = self.client.session[TESTIMONIAL_UPLOAD_SESSION_KEY][nonce]
        receipts = (
            None,
            [self.resource(public_id), self.resource(public_id)],
            {"public_id": f"{public_id}-mismatch", "version": 1, "signature": "signed"},
        )
        for receipt in receipts:
            with self.subTest(receipt=receipt), patch(
                "core.testimonial_uploads.api_sign_request",
                return_value="signed",
            ):
                with self.assertRaises(ValueError):
                    verify_testimonial_upload_receipt(batch, receipt)

    def test_cloudinary_metadata_rejects_unsupported_and_oversized_video(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]
        metadata_cases = [
            self.resource(public_id, file_format="pdf"),
            self.resource(public_id, size=MAX_TESTIMONIAL_VIDEO_BYTES + 1),
            self.resource(public_id, resource_type="image"),
        ]
        for metadata in metadata_cases:
            with (
                self.subTest(metadata=metadata),
                patch("core.testimonial_uploads.api_sign_request", return_value="signed"),
                patch(
                    "core.testimonial_uploads.cloudinary_api.resources_by_ids",
                    return_value={"resources": [metadata]},
                ),
                patch("core.admin.cleanup_testimonial_upload", return_value=True),
            ):
                response = self.client.post(
                    self.upload_url,
                    {
                        "action": "finalize",
                        "nonce": nonce,
                        "item_id": "",
                        "receipt": json.dumps(
                            {
                                "public_id": public_id,
                                "version": 1,
                                "signature": "signed",
                            }
                        ),
                    },
                )
                self.assertEqual(response.status_code, 400)

    def test_cancel_verifies_ownership_and_cleans_the_staged_asset(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]
        with patch("core.admin.cleanup_testimonial_upload", return_value=True) as cleanup:
            response = self.client.post(
                self.upload_url,
                {"action": "cancel", "nonce": nonce, "item_id": ""},
            )

        self.assertEqual(response.status_code, 200)
        cleanup.assert_called_once()
        self.assertNotIn(nonce, self.client.session.get(TESTIMONIAL_UPLOAD_SESSION_KEY, {}))

    def test_cancel_failure_is_reported_and_batch_remains_for_retry(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        with patch("core.admin.cleanup_testimonial_upload", return_value=False):
            response = self.client.post(
                self.upload_url,
                {"action": "cancel", "nonce": nonce, "item_id": ""},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn(nonce, self.client.session[TESTIMONIAL_UPLOAD_SESSION_KEY])

    def test_expired_batches_are_cleaned_when_the_admin_requests_another_upload(self):
        session = self.client.session
        session[TESTIMONIAL_UPLOAD_SESSION_KEY] = {
            "expired": {
                "public_id": "testimonial-videos/admin/expired/asset",
                "user_id": self.admin.pk,
                "item_id": None,
                "expires_at": 1,
                "finalized": False,
            }
        }
        session.save()

        with patch("core.admin.cleanup_testimonial_upload", return_value=True) as cleanup:
            response = self.sign_batch()

        self.assertEqual(response.status_code, 200)
        cleanup.assert_called_once()
        self.assertNotIn("expired", self.client.session[TESTIMONIAL_UPLOAD_SESSION_KEY])

    def test_cleanup_refuses_ids_outside_the_admin_upload_prefix(self):
        with patch(
            "core.testimonial_uploads.cloudinary_api.resources_by_ids"
        ) as resources:
            cleaned = cleanup_testimonial_upload(
                {"public_id": "testimonial-videos/someone-elses-asset"}
            )

        self.assertFalse(cleaned)
        resources.assert_not_called()

    def test_existing_video_can_be_replaced_without_server_reupload(self):
        existing = TestimonialVideo.objects.create(
            title="Replace me",
            video="testimonial-videos/original-video",
        )
        sign_response = self.sign_batch(existing.pk)
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]
        with (
            patch("core.testimonial_uploads.api_sign_request", return_value="signed"),
            patch(
                "core.testimonial_uploads.cloudinary_api.resources_by_ids",
                return_value={"resources": [self.resource(public_id)]},
            ),
        ):
            finalized = self.client.post(
                self.upload_url,
                {
                    "action": "finalize",
                    "nonce": nonce,
                    "item_id": str(existing.pk),
                    "receipt": json.dumps(
                        {
                            "public_id": public_id,
                            "version": 1,
                            "signature": "signed",
                        }
                    ),
                },
            )
        self.assertEqual(finalized.status_code, 200)

        with patch("core.storage.cloudinary.uploader.upload") as upload:
            response = self.client.post(
                reverse("admin:core_testimonialvideo_change", args=[existing.pk]),
                {
                    "title": "Replacement testimonial",
                    "description": "",
                    "active": "on",
                    "video_upload_nonce": nonce,
                },
            )

        self.assertEqual(response.status_code, 302)
        existing.refresh_from_db()
        self.assertEqual(existing.video.name, public_id)
        self.assertEqual(existing.title, "Replacement testimonial")
        upload.assert_not_called()

    def test_database_failure_cleans_verified_asset_and_preserves_no_record(self):
        sign_response = self.sign_batch()
        nonce = sign_response.json()["nonce"]
        public_id = sign_response.json()["upload"]["public_id"]
        self.assertEqual(self.finalize(nonce, public_id).status_code, 200)

        with (
            patch.object(TestimonialVideo, "save", side_effect=RuntimeError("database failure")),
            patch("core.admin.cleanup_testimonial_upload", return_value=True) as cleanup,
            self.assertRaises(RuntimeError),
        ):
            self.client.post(
                self.add_url,
                {
                    "title": "Will fail to save",
                    "description": "",
                    "active": "on",
                    "video_upload_nonce": nonce,
                },
            )

        cleanup.assert_called_once()
        self.assertFalse(TestimonialVideo.objects.filter(title="Will fail to save").exists())

    def test_add_and_change_permissions_are_checked_for_each_target(self):
        existing = TestimonialVideo.objects.create(
            title="Existing",
            video="testimonial-videos/existing.mp4",
        )
        user = get_user_model().objects.create_user(
            username="testimonial-adder",
            password="test-password",
            is_staff=True,
        )
        from django.contrib.auth.models import Permission

        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="core",
                codename="add_testimonialvideo",
            )
        )
        self.client.force_login(user)

        create_response = self.sign_batch()
        change_response = self.sign_batch(existing.pk)

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(change_response.status_code, 403)

    def test_existing_testimonial_video_playback_url_is_unchanged(self):
        video = TestimonialVideo.objects.create(
            title="Existing testimonial",
            video="testimonial-videos/existing-video.mp4",
            active=True,
        )
        playback_url = "https://res.cloudinary.com/test-cloud/video/upload/testimonial-videos/existing-video.mp4"
        with patch(
            "core.storage.cloudinary.utils.cloudinary_url",
            return_value=(playback_url, {}),
        ):
            response = self.client.get(
                reverse("testimonial_video_watch", args=[video.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, playback_url)

    def test_existing_formats_remain_allowed(self):
        self.assertEqual(
            ALLOWED_TESTIMONIAL_VIDEO_FORMATS,
            {"mp4", "mov", "m4v", "webm", "avi", "mkv", "mpeg", "mpg", "ogv", "3gp"},
        )

    def test_admin_form_loads_upload_script_and_controls(self):
        response = self.client.get(self.add_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testimonial-video-upload.js")
        self.assertContains(response, "testimonial-video-progress")
        self.assertContains(response, "data-upload-url")
