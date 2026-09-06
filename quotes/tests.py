from datetime import date, time, timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from quotes.forms import QuoteRequestForm
from quotes.models import QuoteRequest, QuoteImage
from quotes.services import calculate_quote_estimate, create_quote_request
from quotes.services import convert_quote_to_booking
from bookings.models import Booking
from customers.models import Customer


@override_settings(RECAPTCHA_SITE_KEY="test-site-key", RECAPTCHA_SECRET_KEY="test-secret-key")
class QuoteFormTests(TestCase):
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
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertTrue(
            "Upload a valid image" in body
            or "One or more uploaded images could not be processed." in body,
            msg="Expected an image validation or image processing error message",
        )
        self.assertEqual(QuoteRequest.objects.count(), 0)
        self.assertEqual(QuoteImage.objects.count(), 0)


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
