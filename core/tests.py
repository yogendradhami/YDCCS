import json
from datetime import datetime, timedelta
from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import urlsplit

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from core.seo_data import SERVICE_DEFINITIONS
from dashboard.models import CompanySettings
from google_reviews.models import GoogleReview
from services.models import Service
from customers.models import Customer
from core.test_utils import mark_public_email_verified


class AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.breadcrumb_depth = 0
        self.current_anchor = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "nav" and attributes.get("aria-label") == "Breadcrumb":
            self.breadcrumb_depth += 1
        elif tag == "a":
            self.current_anchor = {
                "href": attributes.get("href", ""),
                "class": attributes.get("class", ""),
                "aria_current": attributes.get("aria-current", ""),
                "breadcrumb": self.breadcrumb_depth > 0,
                "text": [],
            }

    def handle_data(self, data):
        if self.current_anchor is not None:
            self.current_anchor["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_anchor is not None:
            self.current_anchor["text"] = "".join(
                self.current_anchor["text"]
            ).strip()
            self.anchors.append(self.current_anchor)
            self.current_anchor = None
        elif tag == "nav" and self.breadcrumb_depth:
            self.breadcrumb_depth -= 1


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
            process=["Inspect the carpet and confirm the requested scope."],
            faqs=[{
                "question": "Can I request carpet steam cleaning?",
                "answer": "Yes. Contact us to discuss your property and requirements.",
            }],
            included=["Deep carpet extraction", "Stain treatment"],
            packages=[{"name": "Standard", "price": "$120"}],
            is_active=True,
        )
        Service.objects.create(
            slug="standard-bathroom-cleaning-adelaide",
            name="Standard Bathroom Cleaning Adelaide",
            description="Bathroom cleaning for Adelaide homes.",
            overview="Cleaning for bathrooms based on the requested scope.",
            introduction="Arrange bathroom cleaning for your property.",
            hero_image="services/standard-bathroom-cleaning-adelaide.jpg",
            process=["Discuss the bathroom cleaning requirements."],
            included=["Bathroom surfaces"],
            packages=[],
            faqs=[],
            is_active=True,
        )

    def assert_internal_links_resolve(
        self,
        response,
        *,
        class_names=(),
        include_breadcrumbs=False,
    ):
        anchors = AnchorCollector()
        anchors.feed(response.content.decode("utf-8"))
        for anchor in anchors.anchors:
            anchor_classes = set(anchor["class"].split())
            if not (
                anchor_classes.intersection(class_names)
                or include_breadcrumbs and anchor["breadcrumb"]
            ):
                continue

            path = urlsplit(anchor["href"]).path
            if path.startswith("/"):
                with self.subTest(internal_link=path):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_root_url_resolves(self):
        response = self.client.get("/")
        # Expect 200 or 302 depending on auth/redirects; assert no server error
        self.assertLess(response.status_code, 500)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        },
    )
    def test_home_page_renders_with_quote_upload_scripts(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("js/fast-image-upload.js", body)
        self.assertIn("js/quote-image-upload.js", body)

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
        sitemap = sitemap_response.content.decode("utf-8")
        self.assertIn("<urlset", sitemap)
        self.assertNotIn("<sitemapindex", sitemap)
        self.assertGreaterEqual(sitemap.count("<url>"), 1790)
        self.assertNotIn("X-Robots-Tag", sitemap_response.headers)
        self.assertIn("public, max-age=86400", sitemap_response["Cache-Control"])

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

    def test_customer_testimonial_video_schema_has_timezone_aware_upload_date(self):
        response = self.client.get(reverse("customer_testimonial_video"))

        self.assertEqual(response.status_code, 200)
        video_schema = json.loads(response.context["video_schema"])
        upload_date = datetime.fromisoformat(video_schema["uploadDate"])

        self.assertIsNotNone(upload_date.tzinfo)
        self.assertIsNotNone(upload_date.utcoffset())

    def test_cleaning_services_video_schema_upload_date_includes_timezone(self):
        response = self.client.get(reverse("cleaning_services_video"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"uploadDate": "2026-08-17T00:00:00+09:30"')

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

    @patch("core.views._get_service_google_reviews", return_value=[])
    def test_service_directory_and_definition_pages_are_reachable(self, _reviews):
        directory = self.client.get(reverse("services_home"))
        self.assertEqual(directory.status_code, 200)

        anchors = AnchorCollector()
        anchors.feed(directory.content.decode("utf-8"))
        directory_service_urls = {
            anchor["href"]
            for anchor in anchors.anchors
            if "btn" in anchor["class"].split()
        }

        expected_slugs = {
            *(f"{slug}-adelaide" for slug in SERVICE_DEFINITIONS),
            "standard-bathroom-cleaning-adelaide",
        }
        for service_slug in expected_slugs:
            service_url = reverse("service_page", args=[service_slug])
            with self.subTest(service_slug=service_slug):
                self.assertIn(service_url, directory_service_urls)
                response = self.client.get(service_url, follow=True)
                self.assertEqual(response.status_code, 200)

                related_anchors = AnchorCollector()
                related_anchors.feed(response.content.decode("utf-8"))
                related_links = [
                    anchor for anchor in related_anchors.anchors
                    if "related-service-card" in anchor["class"].split()
                ]
                self.assertGreaterEqual(len(related_links), 3)
                self.assertLessEqual(len(related_links), 6)

    @patch("core.views._get_service_google_reviews", return_value=[])
    def test_service_page_renders_related_faqs_process_breadcrumbs_and_resources(
        self, _reviews
    ):
        response = self.client.get(
            reverse("service_page", args=["carpet-steam-cleaning-adelaide"])
        )
        self.assertEqual(response.status_code, 200)
        service = response.context["service"]
        self.assertEqual(
            service["process"],
            ["Inspect the carpet and confirm the requested scope."],
        )
        self.assertGreaterEqual(len(response.context["faq_section"]["entries"]), 5)
        self.assertTrue(all(
            package.get("name") and package.get("description")
            for package in service["packages"]
        ))

        body = response.content.decode("utf-8")
        self.assertIn('aria-label="Breadcrumb"', body)
        self.assertIn('"@id": "https://ydcleaning.com.au/#localbusiness"', body)
        self.assertNotIn("Satisfaction Guaranteed", body)
        self.assertNotIn("Happy Adelaide Customers", body)
        self.assertIn("fetchpriority=\"high\"", body)

        anchors = AnchorCollector()
        anchors.feed(body)
        breadcrumb_urls = {
            urlsplit(anchor["href"]).path
            for anchor in anchors.anchors
            if anchor["breadcrumb"]
        }
        self.assertIn(reverse("home"), breadcrumb_urls)
        self.assertIn(reverse("services_home"), breadcrumb_urls)
        self.assert_internal_links_resolve(
            response,
            class_names=("related-service-card", "service-resource-link"),
            include_breadcrumbs=True,
        )

    @patch("core.views._get_service_google_reviews", return_value=[])
    def test_quick_quote_offers_every_defined_service(self, _reviews):
        from quotes.forms import QuickQuoteForm

        service_choices = set(dict(
            QuickQuoteForm.base_fields["service"].choices
        ))
        missing_choices = set(SERVICE_DEFINITIONS) - service_choices
        missing_choices.discard("bathroom-cleaning")
        self.assertFalse(missing_choices)
        self.assertIn("standard-bathroom-cleaning", service_choices)

        response = self.client.get(
            reverse("service_page", args=["bathroom-cleaning-adelaide"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["quick_quote_preset_service"],
            "standard-bathroom-cleaning",
        )

    def test_definition_only_services_are_in_the_sitemap(self):
        sitemap = self.client.get(reverse("sitemap_xml")).content.decode("utf-8")
        self.assertIn("/services/kitchen-deep-cleaning-adelaide/", sitemap)
        self.assertIn("/services/standard-bathroom-cleaning-adelaide/", sitemap)

    def test_controlled_adelaide_local_page_has_unique_seo_metadata(self):
        resp = self.client.get("/local/adelaide/aberfoyle-park-5159/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("Aberfoyle Park Cleaning Services | YD Commercial Cleaning", body)
        self.assertIn("Professional cleaning services in Aberfoyle Park, Adelaide", body)
        self.assertIn("Aberfoyle Park", body)

    def test_adelaide_directory_and_all_letter_pages_link_to_controlled_suburbs(self):
        from core.views import _get_controlled_adelaide_areas

        areas = _get_controlled_adelaide_areas()
        controlled_slugs = {area["slug"] for area in areas}
        hub = self.client.get(reverse("local_area_index_default"))

        self.assertEqual(hub.status_code, 200)
        self.assertContains(hub, "Professional Cleaning Services in Adelaide")
        self.assertEqual(
            {area["slug"] for area in hub.context["related_areas"]},
            controlled_slugs,
        )
        self.assert_internal_links_resolve(
            hub,
            class_names=("adelaide-card-link", "adelaide-suburb-card"),
            include_breadcrumbs=True,
        )
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            url_name = (
                "local_area_index_default"
                if letter == "A"
                else "local_area_index"
            )
            kwargs = {} if letter == "A" else {"letter": letter.lower()}
            self.assertContains(
                hub,
                f'href="{reverse(url_name, kwargs=kwargs)}"',
            )

        for area in hub.context["related_areas"]:
            with self.subTest(suburb=area["slug"]):
                suburb_response = self.client.get(
                    reverse("local_suburb_detail", args=[area["slug"]])
                )
                self.assertEqual(suburb_response.status_code, 200)

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            with self.subTest(letter=letter):
                url_name = (
                    "local_area_index_default"
                    if letter == "A"
                    else "local_area_index"
                )
                kwargs = {} if letter == "A" else {"letter": letter.lower()}
                letter_url = reverse(url_name, kwargs=kwargs)
                response = self.client.get(letter_url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["current_letter"], letter)
                self.assertContains(response, f'href="{letter_url}"')

                anchors = AnchorCollector()
                anchors.feed(response.content.decode("utf-8"))
                active_letters = [
                    anchor
                    for anchor in anchors.anchors
                    if "active" in anchor["class"].split()
                    and anchor["aria_current"] == "page"
                ]
                self.assertEqual(len(active_letters), 1)
                self.assertEqual(active_letters[0]["text"], letter)

                expected_suburbs = {
                    area["slug"]
                    for area in areas
                    if letter == "A" or area["letter"] == letter
                }
                self.assertEqual(
                    {
                        urlsplit(anchor["href"]).path.rsplit("/", 2)[-2]
                        for anchor in anchors.anchors
                        if "adelaide-suburb-card" in anchor["class"].split()
                    },
                    expected_suburbs,
                )

    def test_suburb_pages_have_working_breadcrumbs_and_valid_nearby_links(self):
        from core.views import _get_controlled_adelaide_areas

        controlled_slugs = {
            area["slug"] for area in _get_controlled_adelaide_areas()
        }
        for area_slug in controlled_slugs:
            with self.subTest(suburb=area_slug):
                response = self.client.get(
                    reverse("local_suburb_detail", args=[area_slug])
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    f"Cleaning Services Available in "
                    f"{response.context['suburb_name']}",
                )

                anchors = AnchorCollector()
                anchors.feed(response.content.decode("utf-8"))
                breadcrumb_paths = {
                    urlsplit(anchor["href"]).path
                    for anchor in anchors.anchors
                    if anchor["breadcrumb"]
                }
                self.assertIn(reverse("local_area_index_default"), breadcrumb_paths)
                letter = response.context["suburb"]["letter"]
                letter_url = (
                    reverse("local_area_index_default")
                    if letter == "A"
                    else reverse("local_area_index", args=[letter.lower()])
                )
                self.assertIn(letter_url, breadcrumb_paths)
                self.assert_internal_links_resolve(
                    response,
                    class_names=(
                        "adelaide-card-link",
                        "adelaide-suburb-card",
                    ),
                    include_breadcrumbs=True,
                )

                for nearby_area in response.context["nearby_area_links"]:
                    self.assertIn(nearby_area["slug"], controlled_slugs)
                    nearby_response = self.client.get(
                        reverse(
                            "local_suburb_detail",
                            args=[nearby_area["slug"]],
                        )
                    )
                    self.assertEqual(nearby_response.status_code, 200)

    def test_related_service_links_are_canonical_and_resolve(self):
        response = self.client.get(
            reverse("service_page", args=["commercial-cleaning-adelaide"])
        )
        self.assertEqual(response.status_code, 200)

        anchors = AnchorCollector()
        anchors.feed(response.content.decode("utf-8"))
        related_links = [
            anchor
            for anchor in anchors.anchors
            if "related-service-card" in anchor["class"].split()
        ]
        self.assertGreaterEqual(len(related_links), 3)
        self.assertLessEqual(len(related_links), 6)
        self.assertEqual(
            len({anchor["href"] for anchor in related_links}),
            len(related_links),
        )

        for anchor in related_links:
            with self.subTest(href=anchor["href"]):
                linked_page = self.client.get(anchor["href"])
                self.assertEqual(linked_page.status_code, 200)

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
