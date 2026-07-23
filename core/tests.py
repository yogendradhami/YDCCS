from django.test import TestCase

from dashboard.models import CompanySettings


class SmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        CompanySettings.objects.create(
            business_name="YD Commercial Cleaning Services",
            phone="0430 049 865",
            email="ydcommercialcleaning@gmail.com",
        )

    def test_root_url_resolves(self):
        response = self.client.get("/")
        # Expect 200 or 302 depending on auth/redirects; assert no server error
        self.assertLess(response.status_code, 500)

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
        self.assertIn("Sitemap:", resp.content.decode("utf-8"))

    def test_home_meta_and_og(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("<title", body)
        self.assertIn('meta name="description"', body)
        self.assertIn('property="og:image"', body)
