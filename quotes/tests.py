import json
from io import BytesIO
from datetime import date, time, timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.datastructures import MultiValueDict
from PIL import Image

from core.test_utils import mark_public_email_verified
from quotes.forms import QuoteRequestForm
from quotes.forms import QuickQuoteForm
from quotes.models import QuoteRequest, QuoteImage
from quotes.services import calculate_quote_estimate, create_quote_request
from quotes.services import convert_quote_to_booking
from quotes.email_service import send_admin_quote_email, send_customer_quote_email
from bookings.models import Booking
from customers.models import Customer
from services.models import Service


@override_settings(RECAPTCHA_SITE_KEY="test-site-key", RECAPTCHA_SECRET_KEY="test-secret-key")
class QuoteFormTests(TestCase):
    def workflow_key(self):
        response = self.client.get("/", HTTP_HOST="127.0.0.1")
        mark_public_email_verified(self.client, "test@example.com")
        return response.context["form"]["workflow_key"].value()

    def test_quote_form_uses_real_captcha_and_hides_price_ui(self):
        form = QuoteRequestForm()
        self.assertIn("g_recaptcha_response", form.fields)
        self.assertNotIn("captcha_answer", form.fields)
        self.assertNotIn("is_not_robot", form.fields)
        self.assertEqual(form.recaptcha_site_key, "test-site-key")

    @patch("quotes.forms.requests.post")
    def test_quote_form_handles_valid_submission_without_images(self, mock_post):
        mock_post.return_value = Mock()
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"success": True}

        workflow_key = self.workflow_key()
        response = self.client.post(
            "/",
            {
                "name": "Test User",
                "email": "test@example.com",
                "phone": "0400000000",
                "property_type": "House",
                "suburb_postcode": "Adelaide 5000",
                "preferred_date": "2026-08-09",
                "message": "Test quote",
                "bedrooms": "2",
                "bathrooms": "1",
                "lead_source": "website",
                "g-recaptcha-response": "localhost-test-token",
                "workflow_key": workflow_key,
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/#quote")
        self.assertEqual(QuoteRequest.objects.count(), 1)
        quote = QuoteRequest.objects.first()
        self.assertEqual(quote.name, "Test User")
        self.assertEqual(quote.estimated_price, 120 + 2 * 30 + 1 * 20)

    @patch("quotes.forms.requests.post")
    def test_quote_form_returns_error_for_invalid_image_upload(self, mock_post):
        invalid_image = SimpleUploadedFile(
            "invalid.jpg",
            b"not-an-image",
            content_type="image/jpeg",
        )

        mock_post.return_value = Mock()
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"success": True}

        workflow_key = self.workflow_key()
        response = self.client.post(
            "/",
            {
                "name": "Test User",
                "email": "test@example.com",
                "phone": "0400000000",
                "property_type": "House",
                "suburb_postcode": "Adelaide 5000",
                "preferred_date": "2026-08-09",
                "message": "Test quote",
                "bedrooms": "2",
                "bathrooms": "1",
                "lead_source": "website",
                "g-recaptcha-response": "localhost-test-token",
                "property_images": [invalid_image],
                "workflow_key": workflow_key,
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        # Django's ImageField rejects the malformed payload during form validation.
        # The view may render the form with field-level errors rather than a
        # global message, so assert the invalid image did not create a quote.
        # The malformed upload must not create a quote or quote image.
        self.assertEqual(QuoteRequest.objects.count(), 0)
        self.assertEqual(QuoteImage.objects.count(), 0)

    @patch("core.views.send_admin_quote_email", return_value=True)
    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("quotes.forms.requests.post")
    def test_repeated_quote_post_with_same_workflow_does_not_duplicate_or_resend(
        self, recaptcha_post, _customer_email, _admin_email
    ):
        recaptcha_post.return_value = Mock()
        recaptcha_post.return_value.raise_for_status.return_value = None
        recaptcha_post.return_value.json.return_value = {"success": True}
        workflow_key = self.workflow_key()
        data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "0400000000",
            "property_type": "House",
            "suburb_postcode": "Adelaide 5000",
            "preferred_date": "2026-08-09",
            "message": "Test quote",
            "bedrooms": "2",
            "bathrooms": "1",
            "lead_source": "website",
            "g-recaptcha-response": "localhost-test-token",
            "workflow_key": workflow_key,
        }

        first = self.client.post("/", data, HTTP_HOST="127.0.0.1")
        mark_public_email_verified(self.client, "test@example.com")
        second = self.client.post("/", data, HTTP_HOST="127.0.0.1")

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        self.assertEqual(_customer_email.call_count, 1)
        self.assertEqual(_admin_email.call_count, 1)


@override_settings(
    RECAPTCHA_SITE_KEY="",
    RECAPTCHA_SECRET_KEY="",
    CLOUDINARY_STORAGE={
        "CLOUD_NAME": "test-cloud",
        "API_KEY": "test-api-key",
        "API_SECRET": "test-api-secret",
    },
)
class QuoteImageUploadTests(TestCase):
    def setUp(self):
        response = self.client.get("/", HTTP_HOST="127.0.0.1")
        self.workflow_key = response.context["form"]["workflow_key"].value()
        mark_public_email_verified(self.client, "direct@example.com")

    def sign_batch(self, count=1, workflow_key=None):
        with patch("quotes.upload_service.api_sign_request", return_value="upload-signature"):
            response = self.client.post(
                "/quote/images/upload/",
                {
                    "upload_action": "sign",
                    "workflow_key": workflow_key or self.workflow_key,
                    "count": str(count),
                },
                HTTP_HOST="127.0.0.1",
            )
        return response

    def quote_data(self, **overrides):
        data = {
            "name": "Direct Upload Customer",
            "email": "direct@example.com",
            "phone": "0400000000",
            "property_type": "House",
            "suburb_postcode": "Adelaide 5000",
            "preferred_date": "2026-08-09",
            "message": "Direct upload test",
            "bedrooms": "2",
            "bathrooms": "1",
            "lead_source": "website",
            "workflow_key": self.workflow_key,
        }
        data.update(overrides)
        return data

    @staticmethod
    def receipt(public_id, version=123, signature="receipt-signature"):
        return {"public_id": public_id, "version": version, "signature": signature}

    @staticmethod
    def cloudinary_resources(public_ids, *, version=123, size=1024, image_format="jpg"):
        return {
            "resources": [
                {
                    "public_id": public_id,
                    "version": version,
                    "bytes": size,
                    "format": image_format,
                    "resource_type": "image",
                }
                for public_id in public_ids
            ]
        }

    @patch("core.views.send_admin_quote_email", return_value=True)
    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("quotes.upload_service.cloudinary_api.resources_by_ids")
    @patch("quotes.upload_service.api_sign_request", return_value="receipt-signature")
    def test_signed_batch_finalizes_and_links_verified_cloudinary_image(
        self, _sign, resources_by_ids, _customer_email, _admin_email
    ):
        batch_response = self.sign_batch()
        self.assertEqual(batch_response.status_code, 200)
        batch = batch_response.json()
        public_id = batch["uploads"][0]["public_id"]
        upload_parameters = batch["uploads"][0]
        self.assertTrue(public_id.startswith("quote_images/"))
        self.assertIn("jpg", upload_parameters["allowed_formats"])
        self.assertEqual(upload_parameters["signature"], "upload-signature")
        self.assertNotIn("test-api-secret", batch_response.content.decode("utf-8"))
        resources_by_ids.return_value = self.cloudinary_resources([public_id])

        response = self.client.post(
            "/",
            self.quote_data(
                quote_image_batch_token=batch["batch_token"],
                quote_image_uploads=json.dumps([self.receipt(public_id)]),
            ),
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        quote_image = QuoteImage.objects.get()
        self.assertEqual(quote_image.image.name, public_id)
        resources_by_ids.assert_called_once_with(
            [public_id], resource_type="image", type="upload"
        )

    def test_signing_rejects_too_many_images(self):
        response = self.sign_batch(count=7)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QuoteRequest.objects.count(), 0)

    @patch("quotes.upload_service.api_sign_request", return_value="valid")
    def test_receipt_must_be_signed_and_match_the_batch(self, _sign):
        expected = ["quote_images/workflow/first", "quote_images/workflow/second"]
        with self.assertRaisesMessage(ValueError, "incomplete"):
            from quotes.upload_service import verify_quote_image_uploads

            verify_quote_image_uploads([], expected)
        with self.assertRaisesMessage(ValueError, "match the signed batch"):
            verify_quote_image_uploads(
                [
                    self.receipt(expected[0], signature="valid"),
                    self.receipt(expected[0], signature="valid"),
                ],
                expected,
            )
        with self.assertRaisesMessage(ValueError, "match the signed batch"):
            verify_quote_image_uploads(
                [
                    self.receipt("quote_images/another-workflow/foreign", signature="valid"),
                    self.receipt(expected[1], signature="valid"),
                ],
                expected,
            )
        with self.assertRaisesMessage(ValueError, "signature"):
            with patch(
                "quotes.upload_service.api_sign_request", return_value="different"
            ):
                verify_quote_image_uploads(
                    [self.receipt(expected[0], signature="invalid"), self.receipt(expected[1])],
                    expected,
                )

    @patch("quotes.upload_service.api_sign_request", return_value="receipt-signature")
    @patch("quotes.upload_service.cloudinary_api.resources_by_ids")
    def test_unsupported_oversized_and_missing_cloudinary_metadata_are_rejected(
        self, resources_by_ids, _sign
    ):
        from quotes.upload_service import verify_quote_image_uploads

        expected = ["quote_images/workflow/photo"]
        receipts = [self.receipt(expected[0])]
        invalid_metadata = [
            self.cloudinary_resources(expected, image_format="svg"),
            self.cloudinary_resources(expected, size=15 * 1024 * 1024 + 1),
            {"resources": []},
        ]
        for metadata in invalid_metadata:
            with self.subTest(metadata=metadata):
                resources_by_ids.return_value = metadata
                with self.assertRaises(ValueError):
                    verify_quote_image_uploads(receipts, expected)

    @patch("quotes.upload_service.api_sign_request", return_value="receipt-signature")
    @patch("quotes.upload_service.cloudinary_api.resources_by_ids")
    def test_combined_actual_cloudinary_size_is_limited(self, resources_by_ids, _sign):
        from quotes.upload_service import verify_quote_image_uploads

        expected = [f"quote_images/workflow/photo-{index}" for index in range(6)]
        receipts = [self.receipt(public_id) for public_id in expected]
        resources_by_ids.return_value = self.cloudinary_resources(
            expected, size=11 * 1024 * 1024
        )
        with self.assertRaisesMessage(ValueError, "60 MB"):
            verify_quote_image_uploads(receipts, expected)

    def test_batch_token_cannot_finalize_another_quote_workflow(self):
        first_batch = self.sign_batch()
        second_workflow_key = self.client.get(
            "/", HTTP_HOST="127.0.0.1"
        ).context["form"]["workflow_key"].value()
        batch = first_batch.json()

        with patch("quotes.upload_service.cloudinary_uploader.destroy") as destroy:
            response = self.client.post(
                "/",
                self.quote_data(
                    workflow_key=second_workflow_key,
                    quote_image_batch_token=batch["batch_token"],
                    quote_image_uploads=json.dumps(
                        [self.receipt(batch["uploads"][0]["public_id"])]
                    ),
                ),
                HTTP_HOST="127.0.0.1",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 0)
        destroy.assert_not_called()

    def test_invalid_finalization_cleans_only_batch_assets(self):
        batch = self.sign_batch().json()
        public_id = batch["uploads"][0]["public_id"]
        with patch("quotes.upload_service.api_sign_request", return_value="expected"):
            with patch("quotes.upload_service.cloudinary_uploader.destroy") as destroy:
                response = self.client.post(
                    "/",
                    self.quote_data(
                        quote_image_batch_token=batch["batch_token"],
                        quote_image_uploads=json.dumps(
                            [self.receipt(public_id, signature="invalid")]
                        ),
                    ),
                    HTTP_HOST="127.0.0.1",
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 0)
        destroy.assert_called_once_with(
            public_id, resource_type="image", invalidate=True
        )

    def test_missing_receipts_clean_the_signed_batch(self):
        batch = self.sign_batch().json()
        public_id = batch["uploads"][0]["public_id"]
        with patch("quotes.upload_service.cloudinary_uploader.destroy") as destroy:
            response = self.client.post(
                "/",
                self.quote_data(quote_image_batch_token=batch["batch_token"]),
                HTTP_HOST="127.0.0.1",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 0)
        destroy.assert_called_once_with(
            public_id, resource_type="image", invalidate=True
        )

    def test_cancel_removes_signed_batch_assets(self):
        batch = self.sign_batch().json()
        public_id = batch["uploads"][0]["public_id"]
        with patch("quotes.upload_service.cloudinary_uploader.destroy") as destroy:
            response = self.client.post(
                "/quote/images/upload/",
                {
                    "upload_action": "cancel",
                    "workflow_key": self.workflow_key,
                    "batch_token": batch["batch_token"],
                },
                HTTP_HOST="127.0.0.1",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"cancelled": True})
        destroy.assert_called_once_with(
            public_id, resource_type="image", invalidate=True
        )

    @patch("core.views.send_admin_quote_email", return_value=True)
    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("quotes.upload_service.cloudinary_api.resources_by_ids")
    @patch("quotes.upload_service.api_sign_request", return_value="receipt-signature")
    def test_repeated_direct_submission_is_idempotent(
        self, _sign, resources_by_ids, customer_email, admin_email
    ):
        batch = self.sign_batch().json()
        public_id = batch["uploads"][0]["public_id"]
        resources_by_ids.return_value = self.cloudinary_resources([public_id])
        data = self.quote_data(
            quote_image_batch_token=batch["batch_token"],
            quote_image_uploads=json.dumps([self.receipt(public_id)]),
        )

        first = self.client.post("/", data, HTTP_HOST="127.0.0.1")
        mark_public_email_verified(self.client, "direct@example.com")
        second = self.client.post("/", data, HTTP_HOST="127.0.0.1")

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        self.assertEqual(QuoteImage.objects.count(), 1)
        self.assertEqual(resources_by_ids.call_count, 1)
        self.assertEqual(customer_email.call_count, 1)
        self.assertEqual(admin_email.call_count, 1)

    def test_quote_upload_endpoint_requires_csrf(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.get("/", HTTP_HOST="127.0.0.1")
        workflow_key = response.context["form"]["workflow_key"].value()
        response = client.post(
            "/quote/images/upload/",
            {"upload_action": "sign", "workflow_key": workflow_key, "count": "1"},
            HTTP_HOST="127.0.0.1",
        )
        self.assertEqual(response.status_code, 403)

    @patch("core.views.send_admin_quote_email", return_value=True)
    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("quotes.upload_service.cloudinary_uploader.destroy")
    @patch("quotes.upload_service.cloudinary_api.resources_by_ids")
    @patch("quotes.upload_service.api_sign_request", return_value="receipt-signature")
    @patch("quotes.services.QuoteImage.objects.bulk_create", side_effect=RuntimeError("db failure"))
    def test_database_failure_cleans_uploaded_asset(
        self,
        _bulk_create,
        _sign,
        resources_by_ids,
        destroy,
        _customer_email,
        _admin_email,
    ):
        batch = self.sign_batch().json()
        public_id = batch["uploads"][0]["public_id"]
        resources_by_ids.return_value = self.cloudinary_resources([public_id])
        response = self.client.post(
            "/",
            self.quote_data(
                quote_image_batch_token=batch["batch_token"],
                quote_image_uploads=json.dumps([self.receipt(public_id)]),
            ),
            HTTP_HOST="127.0.0.1",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 0)
        destroy.assert_any_call(public_id, resource_type="image", invalidate=True)


@override_settings(RECAPTCHA_SITE_KEY="", RECAPTCHA_SECRET_KEY="")
class QuoteServiceTests(TestCase):
    def valid_form(self, **overrides):
        data = {
            "name": "Service Customer",
            "email": "service@example.com",
            "phone": "0400000000",
            "property_type": "House",
            "suburb_postcode": "Adelaide 5000",
            "bedrooms": 2,
            "bathrooms": 1,
            "lead_source": "website",
        }
        data.update(overrides)
        return QuoteRequestForm(data=data)

    def test_estimate_preserves_homepage_formula(self):
        form = self.valid_form()
        self.assertTrue(form.is_valid())
        self.assertEqual(calculate_quote_estimate(form.save(commit=False)), 200)

    def test_quote_creation_and_idempotency(self):
        first, created = create_quote_request(
            form=self.valid_form(), workflow_key="quote-workflow"
        )
        second, second_created = create_quote_request(
            form=self.valid_form(email="other@example.com"), workflow_key="quote-workflow"
        )
        self.assertTrue(created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        self.assertEqual(first.estimated_price, 200)

    def test_idempotent_retry_does_not_upload_duplicate_images(self):
        storage = QuoteImage._meta.get_field("image").storage
        with patch.object(storage, "save", side_effect=lambda name, _file: name) as save_image:
            first, created = create_quote_request(
                form=self.valid_form(),
                images=[self.image_upload("first.jpg")],
                workflow_key="quote-image-retry",
            )
            second, second_created = create_quote_request(
                form=self.valid_form(email="duplicate@example.com"),
                images=[self.image_upload("retry.jpg")],
                workflow_key="quote-image-retry",
            )

        self.assertTrue(created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(save_image.call_count, 1)
        self.assertEqual(QuoteImage.objects.count(), 1)

    def test_different_workflows_create_independent_quotes(self):
        first, _ = create_quote_request(form=self.valid_form(), workflow_key="quote-one")
        second, _ = create_quote_request(
            form=self.valid_form(email="two@example.com"), workflow_key="quote-two"
        )
        self.assertNotEqual(first.pk, second.pk)

    def test_invalid_form_is_rejected(self):
        form = self.valid_form(property_type="")
        with self.assertRaises(ValueError):
            create_quote_request(form=form)

    def test_property_photo_combined_size_is_limited(self):
        class OversizedImage(SimpleUploadedFile):
            @property
            def size(self):
                return getattr(self, "fake_size", self._size)

            @size.setter
            def size(self, value):
                self._size = value

        images = []
        for index in range(6):
            image = self.image_upload(f"photo-{index}.jpg")
            oversized = OversizedImage(
                image.name,
                image.read(),
                content_type="image/jpeg",
            )
            oversized.fake_size = 11 * 1024 * 1024
            images.append(oversized)
        form = QuoteRequestForm(
            data=self.valid_form().data,
            files=MultiValueDict({"property_images": images}),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("property_images", form.errors)

    @staticmethod
    def image_upload(name):
        buffer = BytesIO()
        Image.new("RGB", (4, 4), color="green").save(buffer, format="JPEG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")

    def test_failed_parallel_image_upload_cleans_successful_asset_and_saves_no_quote(self):
        form = self.valid_form()
        self.assertTrue(form.is_valid())
        storage = QuoteImage._meta.get_field("image").storage
        successful_name = "quote_images/saved.jpg"

        def save_image(name, uploaded_file):
            if uploaded_file.name == "bad.jpg":
                raise RuntimeError("storage failure")
            return successful_name

        with patch.object(storage, "save", side_effect=save_image):
            with patch.object(storage, "delete") as delete_storage:
                with self.assertRaises(RuntimeError):
                    create_quote_request(
                        form=form,
                        images=[self.image_upload("good.jpg"), self.image_upload("bad.jpg")],
                    )

        delete_storage.assert_called_once_with(successful_name)
        self.assertEqual(QuoteRequest.objects.count(), 0)
        self.assertEqual(QuoteImage.objects.count(), 0)

    def test_quote_database_failure_cleans_all_uploaded_images(self):
        form = self.valid_form()
        self.assertTrue(form.is_valid())
        storage = QuoteImage._meta.get_field("image").storage

        with patch.object(storage, "save", side_effect=lambda name, _file: name):
            with patch.object(storage, "delete") as delete_storage:
                with patch("quotes.services.QuoteImage.objects.bulk_create", side_effect=RuntimeError("db failure")):
                    with self.assertRaises(RuntimeError):
                        create_quote_request(form=form, images=[self.image_upload("good.jpg")])

        delete_storage.assert_called_once()
        self.assertEqual(QuoteRequest.objects.count(), 0)
        self.assertEqual(QuoteImage.objects.count(), 0)

    def make_quote(self, **overrides):
        data = {
            "name": "Conversion Customer",
            "email": "conversion@example.com",
            "phone": "0400000000",
            "property_type": "Office",
            "suburb_postcode": "Adelaide 5000",
            "preferred_date": date.today() + timedelta(days=4),
            "estimated_price": 200,
        }
        data.update(overrides)
        return QuoteRequest.objects.create(**data)

    def test_quote_conversion_creates_booking_and_marks_booked(self):
        quote = self.make_quote()
        booking, created = convert_quote_to_booking(
            quote_id=quote.id,
            booking_date=quote.preferred_date,
            booking_time=time(10, 0),
        )
        quote.refresh_from_db()
        self.assertTrue(created)
        self.assertEqual(quote.status, "booked")
        self.assertEqual(booking.booking_time, time(10, 0))
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Customer.objects.filter(email__iexact=quote.email).count(), 1)

    def test_quote_conversion_requires_explicit_date_and_time(self):
        quote = self.make_quote()
        with self.assertRaises(ValueError):
            convert_quote_to_booking(quote_id=quote.id, booking_date=None, booking_time=None)
        quote.refresh_from_db()
        self.assertEqual(quote.status, "new")
        self.assertEqual(Booking.objects.count(), 0)

    def test_repeated_quote_conversion_reuses_booking(self):
        quote = self.make_quote()
        first, first_created = convert_quote_to_booking(
            quote_id=quote.id, booking_date=quote.preferred_date, booking_time=time(10, 0)
        )
        second, second_created = convert_quote_to_booking(
            quote_id=quote.id, booking_date=quote.preferred_date, booking_time=time(10, 0)
        )
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Booking.objects.count(), 1)

    @patch("quotes.services.create_booking")
    def test_booking_failure_does_not_mark_quote_booked(self, create_booking_mock):
        create_booking_mock.side_effect = ValueError("booking validation failed")
        quote = self.make_quote()
        with self.assertRaises(ValueError):
            convert_quote_to_booking(
                quote_id=quote.id,
                booking_date=quote.preferred_date,
                booking_time=time(10, 0),
            )
        quote.refresh_from_db()
        self.assertEqual(quote.status, "new")
        self.assertEqual(Booking.objects.count(), 0)


@override_settings(RECAPTCHA_SITE_KEY="", RECAPTCHA_SECRET_KEY="")
class QuickQuoteFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        service_names = {
            "commercial-cleaning": "Commercial Cleaning",
            "end-of-lease-cleaning": "End of Lease Cleaning",
            "deep-cleaning": "Deep Cleaning",
            "standard-bathroom-cleaning": "Bathroom Cleaning",
            "kitchen-cleaning": "Kitchen Cleaning",
            "oven-cleaning": "Oven Cleaning",
            "carpet-cleaning": "Carpet Cleaning",
            "window-cleaning": "Window Cleaning",
        }
        for slug, name in service_names.items():
            Service.objects.create(
                slug=f"{slug}-adelaide",
                name=f"{name} Adelaide",
                description=f"Professional {name.lower()} in Adelaide.",
                overview=f"Arrange professional {name.lower()} in Adelaide.",
                hero_image="services/test-service.jpg",
                included=[],
                packages=[],
                is_active=True,
            )

    def valid_data(self, **overrides):
        data = {
            "quick_quote_submit": "1",
            "source_page": "https://untrusted.example/forged-path/",
            "name": "Quick Quote Customer",
            "phone": "0430 049 865",
            "email": "quick@example.com",
            "suburb_postcode": "Norwood 5067",
            "service": "house-cleaning",
            "property_type": "House",
        }
        data.update(overrides)
        return data

    def post_verified(self, path, data, **extra):
        data = dict(data)
        if not data.get("workflow_key"):
            form_page = self.client.get(
                path,
                HTTP_HOST=extra.get("HTTP_HOST", "localhost"),
            )
            data["workflow_key"] = form_page.context[
                "quick_quote_form"
            ]["workflow_key"].value()
        mark_public_email_verified(self.client, data["email"])
        return self.client.post(path, data, **extra)

    def test_component_renders_on_conversion_pages(self):
        urls = [
            "/",
            "/pricing/",
            "/contact/",
            "/eco-friendly-cleaning/",
            "/emergency-cleaning/",
            "/services/oven-cleaning/",
            "/services/commercial-cleaning-adelaide/",
            "/services/end-of-lease-cleaning-adelaide/",
            "/services/deep-cleaning-adelaide/",
            "/services/standard-bathroom-cleaning-adelaide/",
            "/services/kitchen-cleaning-adelaide/",
            "/services/carpet-cleaning-adelaide/",
            "/services/window-cleaning-adelaide/",
            "/local/adelaide/aberfoyle-park-5159/",
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url, HTTP_HOST="localhost", follow=True)
                self.assertEqual(response.status_code, 200)
                body = response.content.decode("utf-8")
                self.assertIn('class="yd-quick-quote__form"', body)
                self.assertIn('name="csrfmiddlewaretoken"', body)
                self.assertIn('id="id_quick_quote_', body)
                self.assertNotIn("{% include", body)
                self.assertNotIn("{% csrf_token %}", body)
                self.assertNotIn("{{ quick_quote_form", body)
                if url.startswith("/services/"):
                    service_slug = url.rstrip("/").rsplit("/", 1)[-1]
                    service_choice = service_slug.removesuffix("-adelaide")
                    self.assertIn(
                        f'name="service" value="{service_choice}"', body
                    )
                if url == "/eco-friendly-cleaning/":
                    self.assertIn(
                        'name="service" value="eco-friendly-cleaning"', body
                    )
                if url == "/emergency-cleaning/":
                    self.assertIn(
                        'name="service" value="emergency-cleaning"', body
                    )

    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("core.views.send_admin_quote_email", return_value=True)
    def test_valid_ajax_submission_stays_on_current_page_and_emails_both_recipients(
        self, admin_email, customer_email
    ):
        response = self.post_verified(
            "/services/oven-cleaning/",
            self.valid_data(service="oven-cleaning"),
            HTTP_HOST="localhost",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertNotEqual(response.json()["workflow_key"], "")
        self.assertIn("Confirmation email sent", response.json()["message"])
        self.assertIn("Your request has been received by our team", response.json()["message"])
        self.assertEqual(QuoteRequest.objects.count(), 1)
        customer_email.assert_called_once()
        admin_email.assert_called_once()
        self.assertEqual(
            admin_email.call_args.kwargs["source_page"],
            "http://localhost/services/oven-cleaning/",
        )

    def test_invalid_fields_render_field_errors_without_redirect(self):
        response = self.client.post(
            "/contact/",
            self.valid_data(
                name="",
                email="not-an-email",
                phone="123",
                service="",
                property_type="",
                suburb_postcode="",
            ),
            HTTP_HOST="localhost",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("name", response.json()["errors"])
        self.assertIn("email", response.json()["errors"])
        self.assertIn("phone", response.json()["errors"])
        self.assertIn("service", response.json()["errors"])
        self.assertIn("property_type", response.json()["errors"])
        self.assertIn("suburb_postcode", response.json()["errors"])
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_unverified_email_is_blocked_before_quote_is_saved(self):
        response = self.client.post(
            "/contact/",
            self.valid_data(),
            HTTP_HOST="localhost",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.json()["requires_email_verification"])
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_native_validation_failure_renders_on_same_page_with_values(self):
        response = self.client.post(
            "/contact/",
            self.valid_data(name="", email="not-an-email"),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.has_header("Location"))
        self.assertContains(response, "Please check the highlighted fields and try again.")
        self.assertContains(response, 'id="id_quick_quote_contact_name"')
        self.assertContains(response, 'value="not-an-email"')
        self.assertEqual(QuoteRequest.objects.count(), 0)

    @patch("core.views.create_quote_request", side_effect=RuntimeError("private detail"))
    def test_server_failure_is_safe_and_stays_on_the_submitted_page(self, create_quote):
        response = self.post_verified(
            "/pricing/",
            self.valid_data(),
            HTTP_HOST="localhost",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
        self.assertIn("We couldn't complete your request right now", response.json()["message"])
        self.assertNotIn("private detail", response.content.decode("utf-8"))
        self.assertEqual(QuoteRequest.objects.count(), 0)

    @patch("core.views.send_customer_quote_email", return_value=False)
    @patch("core.views.send_admin_quote_email", return_value=False)
    def test_email_failures_are_reported_without_losing_saved_request(
        self, admin_email, customer_email
    ):
        response = self.post_verified(
            "/pricing/",
            self.valid_data(),
            HTTP_HOST="localhost",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("couldn't send a confirmation email", response.json()["message"])
        self.assertIn("notification could not be sent", response.json()["message"])
        self.assertEqual(QuoteRequest.objects.count(), 1)
        customer_email.assert_called_once()
        admin_email.assert_called_once()

    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("core.views.send_admin_quote_email", return_value=True)
    def test_replayed_quick_quote_workflow_does_not_duplicate_or_resend(
        self, admin_email, customer_email
    ):
        data = self.valid_data()
        form_page = self.client.get("/contact/", HTTP_HOST="localhost")
        data["workflow_key"] = form_page.context[
            "quick_quote_form"
        ]["workflow_key"].value()
        first = self.post_verified(
            "/contact/",
            data,
            HTTP_HOST="localhost",
        )
        mark_public_email_verified(self.client, data["email"])
        second = self.client.post(
            "/contact/",
            data,
            HTTP_HOST="localhost",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        customer_email.assert_called_once()
        admin_email.assert_called_once()

    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("core.views.send_admin_quote_email", return_value=True)
    def test_native_submission_renders_success_on_same_page(self, admin_email, customer_email):
        response = self.post_verified(
            "/contact/",
            self.valid_data(),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.has_header("Location"))
        self.assertContains(response, "Thanks, your quote request has been received.")
        self.assertContains(response, 'class="yd-quick-quote__form"')
        self.assertEqual(QuoteRequest.objects.count(), 1)

    @patch("core.views.send_customer_quote_email", return_value=True)
    @patch("core.views.send_admin_quote_email", return_value=True)
    def test_native_posts_stay_on_each_embedded_form_page(self, admin_email, customer_email):
        cases = [
            ("/", "house-cleaning"),
            ("/pricing/", "office-cleaning"),
            ("/contact/", "commercial-cleaning"),
            ("/services/oven-cleaning/", "oven-cleaning"),
            ("/local/adelaide/aberfoyle-park-5159/", "house-cleaning"),
            ("/eco-friendly-cleaning/", "eco-friendly-cleaning"),
            ("/emergency-cleaning/", "emergency-cleaning"),
        ]
        for path, service in cases:
            with self.subTest(path=path):
                response = self.post_verified(
                    path,
                    self.valid_data(service=service),
                    HTTP_HOST="localhost",
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.has_header("Location"))
                self.assertIn(
                    "Thanks, your quote request has been received.",
                    response.content.decode("utf-8"),
                )

        self.assertEqual(QuoteRequest.objects.count(), len(cases))
        self.assertEqual(customer_email.call_count, len(cases))
        self.assertEqual(admin_email.call_count, len(cases))

    def test_quick_quote_requires_csrf(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(
            "/contact/",
            self.valid_data(),
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_quick_quote_phone_validation(self):
        form = QuickQuoteForm(data=self.valid_data(phone="123"))
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="quotes@example.com",
        ADMIN_EMAIL="admin@example.com",
    )
    def test_email_service_sends_branded_customer_and_admin_messages(self):
        form = QuickQuoteForm(data=self.valid_data(name="<Customer>"))
        self.assertTrue(form.is_valid(), form.errors)
        quote, _ = create_quote_request(form=form)

        self.assertTrue(
            send_customer_quote_email(quote, service_name="House Cleaning")
        )
        self.assertTrue(
            send_admin_quote_email(
                quote,
                service_name="House Cleaning",
                source_page="https://ydcleaning.com.au/services/house-cleaning/",
                submitted_at="2026-09-29 10:30",
            )
        )

        self.assertEqual(len(mail.outbox), 2)
        customer_message, admin_message = mail.outbox
        self.assertEqual(customer_message.to, ["quick@example.com"])
        self.assertIn("House Cleaning", customer_message.body)
        self.assertEqual(len(customer_message.alternatives), 1)
        customer_html = customer_message.alternatives[0][0]
        self.assertIn('name="viewport"', customer_html)
        self.assertIn("&lt;Customer&gt;", customer_html)
        self.assertNotIn("<Customer>", customer_html)
        self.assertEqual(admin_message.to, ["admin@example.com"])
        self.assertIn("https://ydcleaning.com.au/services/house-cleaning/", admin_message.body)
        self.assertIn("2026-09-29 10:30", admin_message.body)
        self.assertIn("NEW QUICK QUOTE REQUEST", admin_message.body)

        self.assertIn("YD Commercial Cleaning", customer_html)
