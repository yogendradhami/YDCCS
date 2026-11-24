from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from blog.models import BlogPost
from core.sitemaps import (
    AdelaideLocalAreaSitemap,
    AdelaideLocalIndexSitemap,
    AdelaideLocalLetterSitemap,
    BlogPostSitemap,
    GuideSitemap,
    LocalServiceSitemap,
    ServiceDetailSitemap,
    ServicesIndexSitemap,
    StaticViewSitemap,
    _base_service_slug_for_local_page,
    service_page_slugs,
)
from services.models import Service
from core.seo_data import get_curated_service_location_slugs


class CuratedServiceLocationIndexingTests(TestCase):
    def test_service_locations_follow_the_curated_profile(self):
        locations = get_curated_service_location_slugs("bathroom-cleaning")

        self.assertIn("glenelg", locations)
        self.assertIn("prospect", locations)
        self.assertNotIn("aldgate", locations)

    def test_database_only_service_does_not_generate_unprofiled_local_pages(self):
        self.assertEqual(
            get_curated_service_location_slugs("standard-bathroom-cleaning"),
            set(),
        )

    def test_generated_sitemap_uses_only_curated_service_locations(self):
        class ServiceRows:
            def values_list(self, *args, **kwargs):
                return [
                    "carpet-steam-cleaning-adelaide",
                    "standard-bathroom-cleaning-adelaide",
                ]

        service_page_slugs.cache_clear()
        try:
            with patch("core.sitemaps.Service.objects.filter", return_value=ServiceRows()):
                slugs = set(service_page_slugs())
        finally:
            service_page_slugs.cache_clear()

        self.assertIn("carpet-steam-cleaning-adelaide-glenelg", slugs)
        self.assertNotIn("carpet-steam-cleaning-adelaide-aldgate", slugs)
        self.assertFalse(
            any(slug.startswith("standard-bathroom-cleaning-adelaide-") for slug in slugs)
        )


class LocalServiceSitemapPerformanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.updated_at = timezone.now()
        cls.service = Service.objects.create(
            slug="carpet-steam-cleaning-adelaide",
            name="Carpet Steam Cleaning",
            description="Professional carpet steam cleaning.",
            overview="Professional carpet steam cleaning in Adelaide.",
            hero_image="services/carpet-steam-cleaning.jpg",
            is_active=True,
        )
        Service.objects.filter(pk=cls.service.pk).update(
            updated_at=cls.updated_at
        )
        cls.service.refresh_from_db()

    def setUp(self):
        self.service_slugs_patcher = patch(
            "core.sitemaps.service_page_slugs",
            return_value=[
                "carpet-steam-cleaning-adelaide-glenelg",
                "carpet-steam-cleaning-adelaide-norwood",
            ],
        )
        self.service_slugs_patcher.start()

    def tearDown(self):
        self.service_slugs_patcher.stop()

    def test_local_page_slug_removes_only_the_final_area_suffix(self):
        self.assertEqual(
            _base_service_slug_for_local_page(
                "carpet-steam-cleaning-adelaide-glenelg"
            ),
            "carpet-steam-cleaning-adelaide",
        )
        self.assertEqual(
            _base_service_slug_for_local_page(
                "carpet-steam-cleaning-adelaide-adelaide-cbd"
            ),
            "carpet-steam-cleaning-adelaide",
        )

    def test_items_load_service_lastmod_values_with_one_query(self):
        sitemap = LocalServiceSitemap()

        with self.assertNumQueries(1):
            items = sitemap.items()

        self.assertTrue(items)
        self.assertEqual(
            sitemap.lastmod("carpet-steam-cleaning-adelaide-glenelg"),
            self.updated_at,
        )
        self.assertEqual(
            ServiceDetailSitemap().lastmod(self.service),
            self.updated_at,
        )
        self.assertIsNone(
            ServiceDetailSitemap().lastmod("generated-static-service-adelaide")
        )

    def test_lastmod_does_not_query_database_for_each_local_url(self):
        sitemap = LocalServiceSitemap()
        sitemap.items()

        sample_items = [
            "carpet-steam-cleaning-adelaide-glenelg",
            "carpet-steam-cleaning-adelaide-norwood",
            "carpet-steam-cleaning-adelaide-prospect",
            "carpet-steam-cleaning-adelaide-adelaide-cbd",
        ]

        with self.assertNumQueries(0):
            dates = [sitemap.lastmod(item) for item in sample_items]

        self.assertTrue(all(date == self.updated_at for date in dates))

    def test_unknown_service_has_no_fabricated_lastmod(self):
        sitemap = LocalServiceSitemap()
        sitemap.items()

        with self.assertNumQueries(0):
            lastmod = sitemap.lastmod("unknown-service-glenelg")

        self.assertIsNone(lastmod)


class PublicContentSitemapTests(TestCase):
    def test_sitemaps_use_the_configured_canonical_domain(self):
        sitemap = StaticViewSitemap()
        self.assertEqual(sitemap.get_domain(), settings.SITE_URL.split("://", 1)[1])
        self.assertIn("booking", sitemap.items())
        self.assertEqual(sitemap.location("booking"), "/booking/")
        self.assertEqual(sitemap.priority("booking"), 0.8)

    def test_static_sitemaps_do_not_fabricate_lastmod_values(self):
        for sitemap in (
            StaticViewSitemap(),
            ServicesIndexSitemap(),
            AdelaideLocalAreaSitemap(),
            AdelaideLocalIndexSitemap(),
            AdelaideLocalLetterSitemap(),
            GuideSitemap(),
        ):
            with self.subTest(sitemap=type(sitemap).__name__):
                self.assertFalse(hasattr(sitemap, "lastmod"))

        service_sitemap = ServiceDetailSitemap()
        self.assertIsNone(
            service_sitemap.lastmod("static-service-definition-adelaide")
        )

    def test_database_backed_sitemaps_use_real_updated_at(self):
        updated_at = timezone.now() - timedelta(days=30)
        post = BlogPost.objects.create(
            title="Recently updated cleaning guide",
            slug="recently-updated-cleaning-guide",
            content="Published content.",
            published=True,
        )
        BlogPost.objects.filter(pk=post.pk).update(updated_at=updated_at)
        post.refresh_from_db()

        self.assertEqual(BlogPostSitemap().lastmod(post), updated_at)

    def test_guides_sitemap_contains_only_existing_public_guides(self):
        sitemap = GuideSitemap()
        self.assertEqual(
            set(sitemap.items()),
            {
                "end-of-lease-checklist",
                "office-checklist",
                "maintenance-schedule",
                "post-construction-checklist",
                "residential-checklist",
                "window-glass-guide",
            },
        )
        self.assertTrue(
            all(
                sitemap.location(item).startswith("/guides/")
                for item in sitemap.items()
            )
        )

    def test_blog_sitemap_excludes_unpublished_posts(self):
        published = BlogPost.objects.create(
            title="Published cleaning guide",
            slug="published-cleaning-guide",
            content="Published content.",
            published=True,
        )
        BlogPost.objects.create(
            title="Draft cleaning guide",
            slug="draft-cleaning-guide",
            content="Draft content.",
            published=False,
        )

        sitemap = BlogPostSitemap()
        self.assertEqual(list(sitemap.items()), [published])
        self.assertEqual(
            sitemap.location(published),
            "/blog/published-cleaning-guide/",
        )
