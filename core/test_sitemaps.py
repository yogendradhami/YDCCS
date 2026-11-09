from django.test import TestCase
from django.utils import timezone

from core.sitemaps import LocalServiceSitemap, _base_service_slug_for_local_page
from services.models import Service


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

    def test_unknown_service_uses_one_stable_fallback_timestamp(self):
        sitemap = LocalServiceSitemap()
        sitemap.items()

        with self.assertNumQueries(0):
            first = sitemap.lastmod("unknown-service-glenelg")
            second = sitemap.lastmod("unknown-service-norwood")

        self.assertEqual(first, second)
