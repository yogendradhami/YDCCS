from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from dashboard.models import CompanySettings
from google_reviews.models import GoogleReview
from services.models import Service
from customers.models import Customer
from core.test_utils import mark_public_email_verified


class SmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        CompanySettings.objects.create(
            business_name="YD Commercial Cleaning Services",
            phone="0430 049 865",
            email="info@ydcleaning.com.au",
        )
        Service.objects.create(
            slug="carpet-steam-cleaning-adelaide",
            name="Carpet Steam Cleaning",
            description="Professional carpet steam cleaning in Adelaide.",
            overview="Deep-clean carpet steam cleaning for homes and businesses.",
            introduction="Carpet steam cleaning for Adelaide homes and offices.",
            hero_image="services/carpet-steam-cleaning-adelaide.jpg",
            included=["Deep carpet extraction", "Stain treatment"],
            packages=[{"name": "Standard", "price": "$120"}],
            is_active=True,
        )

    def test_root_url_resolves(self):
        response = self.client.get("/")
        # Expect 200 or 302 depending on auth/redirects; assert no server error
        self.assertLess(response.status_code, 500)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
            },
        },
        WHITENOISE_MANIFEST_STRICT=False,
    )
    def test_home_page_renders_without_missing_manifest_entries(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_public_resource_pages(self):
        public_urls = [
            "/resources/",
            "/guides/",
            "/case-studies/",
            "/faq/",
            "/blog/",
            "/corporate/",
            "/insurance/",
            "/referral-program/",
            "/eco-friendly-cleaning/",
            "/emergency-cleaning/",
        ]

        for url in public_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertLess(response.status_code, 500)
                self.assertNotEqual(response.status_code, 404)

    def test_local_redirect_and_rss_feed(self):
        local_response = self.client.get("/local/")
        self.assertLess(local_response.status_code, 500)
        self.assertIn(local_response.status_code, (200, 302))

        rss_response = self.client.get("/rss.xml")
        self.assertEqual(rss_response.status_code, 200)
        self.assertIn(
            "application/rss+xml",
            rss_response["Content-Type"],
        )

    def test_sitemap_route(self):
        sitemap_response = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertIn("xml", sitemap_response["Content-Type"])
        self.assertIn("<urlset", sitemap_response.content.decode("utf-8"))

    def test_robots_exists(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain; charset=utf-8")
        body = resp.content.decode("utf-8")
        self.assertIn("User-agent: *", body)
        self.assertIn("Allow: /", body)
        robots_lines = {
            line.strip()
            for line in body.splitlines()
            if line.strip()
        }
        self.assertNotIn("Disallow: /", robots_lines)
        self.assertIn("Sitemap:", body)

    def test_testimonials_page_includes_live_google_reviews_section(self):
        GoogleReview.objects.create(
            review_id="smoke-test-review",
            reviewer_name="Test Google Reviewer",
            rating="5",
            comment="Excellent cleaning service.",
        )

        resp = self.client.get("/testimonials/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("Recent Google Reviews", body)
        self.assertIn("Excellent cleaning service.", body)

    def test_footer_special_services_section_uses_simple_links(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertNotIn("special-service-card", body)
        self.assertIn("/eco-friendly-cleaning/", body)
        self.assertIn("/emergency-cleaning/", body)
        self.assertIn("/insurance/", body)
        self.assertIn("/referral-program/", body)

    def test_eco_friendly_page_has_modern_sections(self):
        resp = self.client.get("/eco-friendly-cleaning/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("A better cleaning experience for your space", body)
        self.assertIn("A better cleaning experience for your space", body)
        self.assertIn("What we use", body)

    def test_home_meta_and_og(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("<title", body)
        self.assertIn('name="description"', body)
        self.assertIn('property="og:image"', body)

    def test_service_page_has_normalized_adelaide_seo_metadata(self):
        resp = self.client.get("/services/oven-cleaning/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("Oven Cleaning in Adelaide | YD Commercial Cleaning", body)
        self.assertNotIn("Adelaide Adelaide", body)
        self.assertNotIn("in Adelaide, Adelaide.", body)
        self.assertNotIn("Adelaide, Adelaide SA", body)

    def test_service_pages_use_dedicated_seo_metadata_when_available(self):
        cases = [
            ("/services/commercial-cleaning-adelaide/", "Commercial Cleaning Adelaide | Professional Business Cleaners"),
            ("/services/office-cleaning-adelaide/", "Office Cleaning Adelaide | Professional Office Cleaners"),
        ]
        for url, expected_title in cases:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                body = resp.content.decode("utf-8")
                self.assertIn(expected_title, body)
                self.assertNotIn("Adelaide Adelaide", body)

    def test_controlled_adelaide_local_page_has_unique_seo_metadata(self):
        resp = self.client.get("/local/adelaide/aberfoyle-park-5159/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("Aberfoyle Park Cleaning Services | YD Commercial Cleaning", body)
        self.assertIn("Professional cleaning services in Aberfoyle Park, Adelaide", body)
        self.assertIn("Aberfoyle Park", body)

    def test_adelaide_local_area_sitemap_contains_controlled_pages(self):
        sitemap = self.client.get("/sitemap.xml").content.decode("utf-8")
        self.assertIn("/local/adelaide/aberfoyle-park-5159/", sitemap)

    def test_related_services_prefer_existing_adelaide_urls(self):
        from core.views import _normalize_related_services

        links = _normalize_related_services(["carpet-steam-cleaning"], "Adelaide")
        self.assertTrue(links)
        self.assertEqual(links[0]["slug"], "carpet-steam-cleaning-adelaide")

    def test_canonical_url_uses_configured_preferred_domain(self):
        from core.templatetags.seo_tags import canonical_url
        from django.test import RequestFactory
        from django.conf import settings

        request = RequestFactory().get("/services/commercial-cleaning-adelaide/", HTTP_HOST="www.example.com")
        url = canonical_url({"request": request})
        self.assertEqual(url, f"{settings.SITE_URL}/services/commercial-cleaning-adelaide/")

    def test_service_page_accepts_adelaide_url_variants(self):
        resp = self.client.get("/services/commercial-cleaning-adelaide/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("Commercial Cleaning", body)

    def test_legacy_service_location_urls_redirect_to_adelaide_canonical(self):
        legacy_cases = [
            ("/services/carpet-steam-cleaning-glenelg/", "/services/carpet-steam-cleaning-adelaide-glenelg/"),
            ("/services/carpet-steam-cleaning-norwood/", "/services/carpet-steam-cleaning-adelaide-norwood/"),
            ("/services/carpet-steam-cleaning-prospect/", "/services/carpet-steam-cleaning-adelaide-prospect/"),
            ("/services/carpet-steam-cleaning-modbury/", "/services/carpet-steam-cleaning-adelaide-modbury/"),
        ]

        for legacy_url, canonical_url in legacy_cases:
            with self.subTest(legacy_url=legacy_url):
                resp = self.client.get(legacy_url, follow=False)
                self.assertEqual(resp.status_code, 301)
                self.assertEqual(resp["Location"], canonical_url)

    def test_canonical_service_urls_remain_200_and_self_referential(self):
        canonical_urls = [
            "/services/carpet-steam-cleaning-adelaide-glenelg/",
            "/services/carpet-steam-cleaning-adelaide-norwood/",
            "/services/carpet-steam-cleaning-adelaide-prospect/",
            "/services/carpet-steam-cleaning-adelaide-modbury/",
        ]

        for canonical_url in canonical_urls:
            with self.subTest(canonical_url=canonical_url):
                resp = self.client.get(canonical_url, follow=False)
                self.assertEqual(resp.status_code, 200)
                self.assertIn(
                    f'<link rel="canonical" href="{settings.SITE_URL}{canonical_url}">',
                    resp.content.decode("utf-8"),
                )

                redirected = self.client.get(canonical_url, follow=True)
                self.assertEqual(redirected.status_code, 200)
                self.assertEqual(redirected.redirect_chain, [])

    def test_sitemap_uses_adelaide_prefixed_local_service_urls(self):
        sitemap = self.client.get("/sitemap.xml").content.decode("utf-8")
        self.assertIn("/services/carpet-steam-cleaning-adelaide-glenelg/", sitemap)
        self.assertNotIn("/services/carpet-steam-cleaning-glenelg/", sitemap)


class PublicBookingWorkflowTests(TestCase):
    def booking_data(self, workflow_key):
        return {
            "workflow_key": workflow_key,
            "name": "Booking Customer",
            "email": "booking.public@example.com",
            "phone": "0400000000",
            "service_type": "Office Cleaning",
            "booking_date": (timezone.localdate() + timedelta(days=5)).isoformat(),
            "booking_time": "10:00",
            "address": "1 King Street",
            "suburb_postcode": "Adelaide 5000",
            "notes": "Please call on arrival.",
        }

    def test_public_booking_page_renders_the_public_customer_fields(self):
        response = self.client.get(reverse("booking"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].is_bound is False)
        for field in ("name", "email", "phone", "workflow_key"):
            self.assertIn(field, response.context["form"].fields)

    @patch("google_reviews.calendar_utils.create_or_update_booking_event")
    @patch("core.views.send_booking_request_email", return_value=True)
    def test_replaying_public_booking_does_not_duplicate_or_repeat_side_effects(
        self, send_email, calendar_sync
    ):
        form_page = self.client.get(reverse("booking"))
        workflow_key = form_page.context["form"]["workflow_key"].value()
        data = self.booking_data(workflow_key)

        mark_public_email_verified(self.client, data["email"])
        first = self.client.post(reverse("booking"), data)
        mark_public_email_verified(self.client, data["email"])
        second = self.client.post(reverse("booking"), data)

        self.assertRedirects(first, reverse("home"))
        self.assertRedirects(second, reverse("home"))
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        send_email.assert_called_once()
        calendar_sync.assert_called_once()

    @patch("core.views.create_booking", side_effect=RuntimeError("private failure"))
    def test_booking_failure_rolls_back_customer_and_hides_exception(self, _create_booking):
        form_page = self.client.get(reverse("booking"))
        data = self.booking_data(
            form_page.context["form"]["workflow_key"].value()
        )
        mark_public_email_verified(self.client, data["email"])

        response = self.client.post(reverse("booking"), data)

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "We couldn&#x27;t complete your booking request", status_code=500)
        self.assertNotContains(response, "private failure", status_code=500)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Booking.objects.count(), 0)
