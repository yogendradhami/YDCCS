from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from quotes.models import QuoteRequest, QuoteImage


class QuoteFormTests(TestCase):
    def test_quote_form_handles_valid_submission_without_images(self):
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
                "is_not_robot": "on",
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/#quote")
        self.assertEqual(QuoteRequest.objects.count(), 1)
        quote = QuoteRequest.objects.first()
        self.assertEqual(quote.name, "Test User")
        self.assertEqual(quote.estimated_price, 120 + 2 * 30 + 1 * 20)

    def test_quote_form_returns_error_for_invalid_image_upload(self):
        invalid_image = SimpleUploadedFile(
            "invalid.jpg",
            b"not-an-image",
            content_type="image/jpeg",
        )

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
                "is_not_robot": "on",
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
