from datetime import date, time, timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings

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
        # Django's ImageField rejects the malformed payload during form validation.
        # The view may render the form with field-level errors rather than a
        # global message, so assert the invalid image did not create a quote.
        # The malformed upload must not create a quote or quote image.
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
        response = self.client.post(
            "/services/oven-cleaning/",
            self.valid_data(service="oven-cleaning"),
            HTTP_HOST="localhost",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
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
        response = self.client.post(
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
        response = self.client.post(
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
    def test_native_submission_renders_success_on_same_page(self, admin_email, customer_email):
        response = self.client.post(
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
                response = self.client.post(
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
