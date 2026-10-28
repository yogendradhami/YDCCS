from io import BytesIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from PIL import Image

from gallery.forms import GalleryItemForm
from gallery.models import GalleryImage, GalleryItem
from gallery.upload_services import (
    ALLOWED_GALLERY_FORMATS,
    GALLERY_UPLOAD_SESSION_KEY,
    MAX_GALLERY_IMAGES,
    _delete_gallery_assets,
    save_gallery_uploads,
    save_verified_gallery_uploads,
    verify_gallery_upload_receipts,
)
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

    def test_edit_cannot_add_more_than_twenty_additional_images_total(self):
        item = GalleryItem.objects.create(
            title="Gallery",
            service_type="House Cleaning",
            source="manual",
        )
        GalleryImage.objects.bulk_create(
            [
                GalleryImage(gallery=item, image=f"gallery/multiple/{index}.jpg")
                for index in range(20)
            ]
        )
        form = GalleryItemForm(
            data={"title": item.title, "service_type": item.service_type, "source": "manual"},
            files=MultiValueDict({"additional_images": [self.image_file()]}),
            instance=item,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("additional_images", form.errors)


@override_settings(
    CLOUDINARY_STORAGE={
        "CLOUD_NAME": "test-cloud",
        "API_KEY": "test-key",
        "API_SECRET": "test-secret-not-a-production-credential",
    }
)
class GalleryDirectUploadTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="gallery-manager",
            password="test-password",
            is_staff=True,
        )
        permissions = Permission.objects.filter(
            Q(
                content_type__app_label="gallery",
                codename__in=("add_galleryitem", "change_galleryitem"),
            )
            | Q(
                content_type__app_label="security",
                codename="access_dashboard",
            )
        )
        self.staff.user_permissions.add(*permissions)
        self.client.force_login(self.staff)
        self.batch_url = reverse("gallery_upload_batch")

    def _sign(self, slots, item_id=None):
        with patch("gallery.upload_services.api_sign_request", return_value="signed"):
            return self.client.post(
                self.batch_url,
                {
                    "upload_action": "sign",
                    "slots": json.dumps(slots),
                    "item_id": "" if item_id is None else str(item_id),
                },
            )

    def _finalize(self, nonce, receipts, resources):
        with (
            patch("gallery.upload_services.api_sign_request", return_value="signed"),
            patch(
                "gallery.upload_services.cloudinary_api.resources_by_ids",
                return_value={"resources": resources},
            ),
        ):
            return self.client.post(
                self.batch_url,
                {
                    "upload_action": "finalize",
                    "nonce": nonce,
                    "item_id": "",
                    "receipts": json.dumps(receipts),
                },
            )

    @staticmethod
    def _resource(public_id, *, image_format="jpg", size=1024, version=1):
        return {
            "public_id": public_id,
            "format": image_format,
            "bytes": size,
            "version": version,
            "resource_type": "image",
            "type": "upload",
        }

    def test_staff_can_sign_a_server_named_gallery_upload_batch(self):
        response = self._sign(["image", "before_image", "after_image", "additional_images"])

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["uploads"]), 4)
        self.assertEqual(
            {upload["slot"] for upload in payload["uploads"]},
            {"image", "before_image", "after_image", "additional_images"},
        )
        for upload in payload["uploads"]:
            self.assertTrue(upload["public_id"].startswith("gallery/admin/"))
            self.assertEqual(upload["signature"], "signed")
            self.assertNotIn("api_secret", upload)

    def test_staff_without_gallery_permission_cannot_use_upload_endpoint(self):
        user = get_user_model().objects.create_user(
            username="unprivileged-staff",
            password="test-password",
            is_staff=True,
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="security",
                codename="access_dashboard",
            )
        )
        self.client.force_login(user)

        response = self._sign(["image"])

        self.assertEqual(response.status_code, 403)

    def test_create_permission_allows_create_batch_but_not_edit_batch(self):
        user = get_user_model().objects.create_user(
            username="gallery-creator",
            password="test-password",
            is_staff=True,
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="security",
                codename="access_dashboard",
            ),
            Permission.objects.get(
                content_type__app_label="gallery",
                codename="add_galleryitem",
            ),
        )
        self.client.force_login(user)

        create_response = self._sign(["image"])
        item = GalleryItem.objects.create(
            title="Existing gallery",
            service_type="House Cleaning",
            source="manual",
        )
        edit_response = self._sign(["image"], item.pk)

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(edit_response.status_code, 403)

    def test_gallery_form_renders_direct_upload_controls(self):
        response = self.client.get(reverse("add_gallery_item"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "gallery-direct-upload.js")
        self.assertContains(response, "data-upload-url")
        self.assertContains(response, "Additional gallery images")

    def test_edit_form_shows_remove_controls_for_saved_gallery_images(self):
        item = GalleryItem.objects.create(
            title="Saved media",
            service_type="House Cleaning",
            source="manual",
            image="gallery/admin/saved/main.jpg",
            before_image="gallery/admin/saved/before.jpg",
            after_image="gallery/admin/saved/after.jpg",
        )
        GalleryImage.objects.create(
            gallery=item,
            image="gallery/admin/saved/additional.jpg",
        )

        response = self.client.get(reverse("edit_gallery_item", args=[item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-remove-saved-slot="image"')
        self.assertContains(response, 'data-remove-saved-slot="before_image"')
        self.assertContains(response, 'data-remove-saved-slot="after_image"')
        self.assertContains(
            response,
            f'data-remove-saved-additional="{GalleryImage.objects.get(gallery=item).pk}"',
        )

    def test_staff_can_remove_saved_primary_and_additional_gallery_images(self):
        item = GalleryItem.objects.create(
            title="Saved media",
            service_type="House Cleaning",
            source="manual",
            image="gallery/admin/saved/main.jpg",
        )
        additional = GalleryImage.objects.create(
            gallery=item,
            image="gallery/admin/saved/additional.jpg",
        )

        primary_response = self.client.post(
            self.batch_url,
            {
                "upload_action": "remove_saved",
                "item_id": item.pk,
                "slot": "image",
            },
        )
        additional_response = self.client.post(
            self.batch_url,
            {
                "upload_action": "remove_saved",
                "item_id": item.pk,
                "slot": "additional_images",
                "image_id": additional.pk,
            },
        )

        self.assertEqual(primary_response.status_code, 200)
        self.assertEqual(additional_response.status_code, 200)
        item.refresh_from_db()
        self.assertFalse(item.image)
        self.assertFalse(GalleryImage.objects.filter(pk=additional.pk).exists())

    def test_saved_gallery_image_removal_requires_change_permission(self):
        item = GalleryItem.objects.create(
            title="Saved media",
            service_type="House Cleaning",
            source="manual",
            image="gallery/admin/saved/main.jpg",
        )
        user = get_user_model().objects.create_user(
            username="gallery-read-only",
            password="test-pass123",
            is_staff=True,
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="security",
                codename="access_dashboard",
            ),
            Permission.objects.get(
                content_type__app_label="gallery",
                codename="add_galleryitem",
            ),
        )
        self.client.force_login(user)

        response = self.client.post(
            self.batch_url,
            {
                "upload_action": "remove_saved",
                "item_id": item.pk,
                "slot": "image",
            },
        )

        self.assertEqual(response.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.image.name, "gallery/admin/saved/main.jpg")

    def test_upload_batch_rejects_more_than_twenty_three_images(self):
        response = self._sign(["additional_images"] * (MAX_GALLERY_IMAGES + 1))

        self.assertEqual(response.status_code, 400)
        self.assertIn("23", response.json()["error"])

    def test_upload_batch_rejects_too_many_additional_images_for_existing_item(self):
        item = GalleryItem.objects.create(
            title="Full gallery",
            service_type="House Cleaning",
            source="manual",
        )
        GalleryImage.objects.bulk_create(
            [
                GalleryImage(gallery=item, image=f"gallery/multiple/{index}.jpg")
                for index in range(20)
            ]
        )

        response = self._sign(["additional_images"], item.pk)

        self.assertEqual(response.status_code, 400)
        self.assertIn("20 additional", response.json()["error"])

    def test_successful_finalize_verifies_cloudinary_receipts_and_metadata(self):
        sign_response = self._sign(["image"])
        nonce = sign_response.json()["nonce"]
        expected = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"]
        public_id = expected[0]["public_id"]

        response = self._finalize(
            nonce,
            [{"public_id": public_id, "version": 1, "signature": "signed"}],
            [self._resource(public_id)],
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["finalized"])
        self.assertEqual(len(self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["verified_assets"]), 1)

    def test_removing_staged_image_cleans_only_that_verified_batch_asset(self):
        sign_response = self._sign(["image", "additional_images"])
        nonce = sign_response.json()["nonce"]
        expected = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"]
        public_id = expected[0]["public_id"]
        finalize_response = self._finalize(
            nonce,
            [
                {"public_id": entry["public_id"], "version": 1, "signature": "signed"}
                for entry in expected
            ],
            [self._resource(entry["public_id"]) for entry in expected],
        )
        self.assertEqual(finalize_response.status_code, 200)

        with patch("gallery.views._delete_gallery_assets", return_value=True) as cleanup:
            response = self.client.post(
                self.batch_url,
                {
                    "upload_action": "remove",
                    "nonce": nonce,
                    "item_id": "",
                    "public_id": public_id,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["remaining"], 1)
        cleanup.assert_called_once_with([public_id])
        remaining = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]
        self.assertEqual(
            [asset["public_id"] for asset in remaining["verified_assets"]],
            [expected[1]["public_id"]],
        )

    def test_staged_image_removal_rejects_cross_batch_public_id(self):
        sign_response = self._sign(["image"])
        nonce = sign_response.json()["nonce"]
        expected = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"]
        self._finalize(
            nonce,
            [{"public_id": expected[0]["public_id"], "version": 1, "signature": "signed"}],
            [self._resource(expected[0]["public_id"])],
        )

        with patch("gallery.views._delete_gallery_assets") as cleanup:
            response = self.client.post(
                self.batch_url,
                {
                    "upload_action": "remove",
                    "nonce": nonce,
                    "item_id": "",
                    "public_id": "gallery/admin/another-batch/asset",
                },
            )

        self.assertEqual(response.status_code, 400)
        cleanup.assert_not_called()

    def test_failed_staged_image_cleanup_keeps_the_batch_attached_to_the_session(self):
        sign_response = self._sign(["image"])
        nonce = sign_response.json()["nonce"]
        expected = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"]
        public_id = expected[0]["public_id"]
        self._finalize(
            nonce,
            [{"public_id": public_id, "version": 1, "signature": "signed"}],
            [self._resource(public_id)],
        )

        with patch("gallery.views._delete_gallery_assets", return_value=False):
            response = self.client.post(
                self.batch_url,
                {
                    "upload_action": "remove",
                    "nonce": nonce,
                    "item_id": "",
                    "public_id": public_id,
                },
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn(nonce, self.client.session[GALLERY_UPLOAD_SESSION_KEY])

    def test_gallery_cleanup_never_deletes_an_asset_attached_to_a_record(self):
        public_id = "gallery/admin/owned-batch/attached"
        item = GalleryItem.objects.create(
            title="Existing gallery",
            service_type="House Cleaning",
            source="manual",
            image=public_id,
        )

        with (
            patch(
                "core.media_cleanup._cloudinary_file_fields",
                return_value=[
                    (GalleryItem, GalleryItem._meta.get_field("image")),
                ],
            ),
            patch("gallery.upload_services.cloudinary_uploader.destroy") as destroy,
        ):
            cleaned = _delete_gallery_assets([public_id])

        self.assertFalse(cleaned)
        destroy.assert_not_called()
        item.refresh_from_db()
        self.assertEqual(item.image.name, public_id)

    def test_invalid_signature_rejects_and_cleans_only_the_signed_asset(self):
        sign_response = self._sign(["image"])
        nonce = sign_response.json()["nonce"]
        public_id = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"][0]["public_id"]
        with patch("gallery.views._delete_gallery_assets") as cleanup:
            response = self._finalize(
                nonce,
                [{"public_id": public_id, "version": 1, "signature": "invalid"}],
                [self._resource(public_id)],
            )

        self.assertEqual(response.status_code, 400)
        cleanup.assert_called_once_with([public_id])

    def test_cross_batch_public_id_is_rejected(self):
        sign_response = self._sign(["image"])
        nonce = sign_response.json()["nonce"]
        expected_id = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"][0]["public_id"]
        with patch("gallery.views._delete_gallery_assets") as cleanup:
            response = self._finalize(
                nonce,
                [{"public_id": "gallery/admin/another-batch/asset", "version": 1, "signature": "signed"}],
                [],
            )

        self.assertEqual(response.status_code, 400)
        cleanup.assert_called_once_with([expected_id])

    def test_missing_and_duplicate_upload_receipts_are_rejected(self):
        expected = [
            {"slot": "image", "public_id": "gallery/admin/batch/main"},
            {"slot": "additional_images", "public_id": "gallery/admin/batch/extra"},
        ]
        with patch("gallery.upload_services.api_sign_request", return_value="signed"):
            with self.assertRaisesMessage(ValueError, "incomplete"):
                verify_gallery_upload_receipts([], expected)
            with self.assertRaisesMessage(ValueError, "match"):
                verify_gallery_upload_receipts(
                    [
                        {"public_id": expected[0]["public_id"], "version": 1, "signature": "signed"},
                        {"public_id": expected[0]["public_id"], "version": 1, "signature": "signed"},
                    ],
                    expected,
                )

    def test_cloudinary_metadata_rejects_invalid_format_and_oversized_file(self):
        public_id = "gallery/admin/batch/main"
        receipt = [{"public_id": public_id, "version": 1, "signature": "signed"}]
        for metadata in (
            self._resource(public_id, image_format="pdf"),
            self._resource(public_id, size=20 * 1024 * 1024 + 1),
            {**self._resource(public_id), "resource_type": "raw"},
        ):
            with (
                patch("gallery.upload_services.api_sign_request", return_value="signed"),
                patch(
                    "gallery.upload_services.cloudinary_api.resources_by_ids",
                    return_value={"resources": [metadata]},
                ),
                self.subTest(format=metadata["format"], size=metadata["bytes"]),
            ):
                with self.assertRaises(ValueError):
                    verify_gallery_upload_receipts(receipt, [{"slot": "image", "public_id": public_id}])

    def test_verified_assets_fill_all_slots_and_additional_image_rows(self):
        item = GalleryItem(
            title="Direct upload",
            service_type="House Cleaning",
            source="manual",
        )
        verified = [
            {"slot": "image", "public_id": "gallery/admin/batch/main"},
            {"slot": "before_image", "public_id": "gallery/admin/batch/before"},
            {"slot": "after_image", "public_id": "gallery/admin/batch/after"},
            {"slot": "additional_images", "public_id": "gallery/admin/batch/extra"},
        ]

        save_verified_gallery_uploads(item, verified)

        item.refresh_from_db()
        self.assertEqual(item.image.name, verified[0]["public_id"])
        self.assertEqual(item.before_image.name, verified[1]["public_id"])
        self.assertEqual(item.after_image.name, verified[2]["public_id"])
        self.assertEqual(
            list(item.additional_images.values_list("image", flat=True)),
            [verified[3]["public_id"]],
        )

    def test_verified_edit_preserves_images_not_replaced_in_the_batch(self):
        item = GalleryItem.objects.create(
            title="Existing gallery",
            service_type="House Cleaning",
            source="manual",
            image="gallery/admin/existing/main",
            after_image="gallery/admin/existing/after",
        )

        save_verified_gallery_uploads(
            item,
            [{"slot": "before_image", "public_id": "gallery/admin/new/before"}],
        )
        item.refresh_from_db()

        self.assertEqual(item.image.name, "gallery/admin/existing/main")
        self.assertEqual(item.after_image.name, "gallery/admin/existing/after")
        self.assertEqual(item.before_image.name, "gallery/admin/new/before")

    def test_database_failure_cleans_unclaimed_cloudinary_assets(self):
        item = GalleryItem(
            title="Failed gallery",
            service_type="House Cleaning",
            source="manual",
        )
        public_id = "gallery/admin/batch/main"
        with (
            patch.object(GalleryItem, "save", side_effect=RuntimeError("database failure")),
            patch("gallery.upload_services._delete_gallery_assets") as cleanup,
            self.assertRaises(RuntimeError),
        ):
            save_verified_gallery_uploads(
                item,
                [{"slot": "image", "public_id": public_id}],
            )

        cleanup.assert_called_once_with([public_id])

    def test_cancel_only_deletes_assets_in_the_session_batch(self):
        sign_response = self._sign(["image"])
        nonce = sign_response.json()["nonce"]
        public_id = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"][0]["public_id"]
        with patch("gallery.views._delete_gallery_assets") as cleanup:
            response = self.client.post(
                self.batch_url,
                {
                    "upload_action": "cancel",
                    "nonce": nonce,
                    "item_id": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["cancelled"])
        cleanup.assert_called_once_with([public_id])

    def test_create_view_attaches_finalized_batch_without_reuploading(self):
        sign_response = self._sign(["image", "additional_images"])
        nonce = sign_response.json()["nonce"]
        expected = self.client.session[GALLERY_UPLOAD_SESSION_KEY][nonce]["expected"]
        with (
            patch("gallery.upload_services.api_sign_request", return_value="signed"),
            patch(
                "gallery.upload_services.cloudinary_api.resources_by_ids",
                return_value={
                    "resources": [self._resource(entry["public_id"]) for entry in expected]
                },
            ),
        ):
            finalized = self.client.post(
                self.batch_url,
                {
                    "upload_action": "finalize",
                    "nonce": nonce,
                    "item_id": "",
                    "receipts": json.dumps(
                        [
                            {"public_id": entry["public_id"], "version": 1, "signature": "signed"}
                            for entry in expected
                        ]
                    ),
                },
            )
        self.assertEqual(finalized.status_code, 200)

        with patch("gallery.upload_services.cloudinary_uploader.upload") as cloudinary_upload:
            response = self.client.post(
                reverse("add_gallery_item"),
                {
                    "gallery_upload_nonce": nonce,
                    "title": "Directly uploaded gallery",
                    "service_type": "House Cleaning",
                    "source": "manual",
                    "featured": "on",
                },
            )

        self.assertEqual(response.status_code, 302)
        item = GalleryItem.objects.get(title="Directly uploaded gallery")
        self.assertEqual(item.image.name, expected[0]["public_id"])
        self.assertEqual(item.additional_images.count(), 1)
        cloudinary_upload.assert_not_called()

    def test_edit_view_preserves_existing_images_without_replacement(self):
        item = GalleryItem.objects.create(
            title="Preserved gallery",
            service_type="House Cleaning",
            source="manual",
            image="gallery/admin/existing/main",
            before_image="gallery/admin/existing/before",
        )

        response = self.client.post(
            reverse("edit_gallery_item", args=[item.pk]),
            {
                "title": "Preserved gallery updated",
                "service_type": "House Cleaning",
                "source": "manual",
                "featured": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.image.name, "gallery/admin/existing/main")
        self.assertEqual(item.before_image.name, "gallery/admin/existing/before")

    def test_supported_format_allowlist_includes_server_converted_heic(self):
        self.assertTrue({"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"} <= ALLOWED_GALLERY_FORMATS)
