from django.test import TestCase
from django.utils import timezone

from blog.models import BlogPost


class BlogPageTests(TestCase):
    def test_blog_detail_renders_for_valid_published_slug(self):
        post = BlogPost.objects.create(
            title="Summer Cleaning Tips for Adelaide's Hot Climate",
            slug="summer-cleaning-adelaide",
            excerpt="Practical cleaning strategies for Adelaide's summer weather.",
            content="<p>Keep your home fresh and hygienic during the hot months.</p>",
            category="Seasonal",
            published=True,
            published_at=timezone.now(),
        )

        response = self.client.get(f"/blog/{post.slug}/")

        self.assertEqual(response.status_code, 200)

    def test_construction_cleaning_article_is_rendered_as_polished_html(self):
        BlogPost.objects.create(
            title="Construction Cleaning Services in Adelaide: Complete Guide for Builders and Property Owners",
            slug="construction-cleaning-services-adelaide",
            excerpt="Discover how professional construction cleaning services help builders, contractors, and property owners prepare newly built or renovated spaces for safe, clean, and ready-to-use environments.",
            content="<h2>What Is Construction Cleaning?</h2><p>Construction cleaning is a specialist service designed to remove dust, debris, building residue, and waste left behind after renovation or build work.</p><p>It is a more detailed process than regular cleaning because it targets areas affected by heavy trade activity and prepares the property for safe handover.</p>",
            category="Residential",
            published=True,
            published_at=timezone.now(),
        )

        response = self.client.get("/blog/construction-cleaning-services-adelaide/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What Is Construction Cleaning?")
        self.assertNotContains(response, "# Construction Cleaning Services")

    def test_blog_detail_renders_for_known_blog_articles(self):
        BlogPost.objects.create(
            title="Summer Cleaning Tips for Adelaide's Hot Climate",
            slug="summer-cleaning-adelaide",
            excerpt="Practical cleaning strategies for Adelaide's summer weather.",
            content="<p>Keep your home fresh and hygienic during the hot months.</p>",
            category="Seasonal",
            published=True,
            published_at=timezone.now(),
        )
        BlogPost.objects.create(
            title="Deep Cleaning vs. Regular Cleaning: When You Need Each",
            slug="deep-cleaning-vs-regular-cleaning",
            excerpt="Learn the differences between deep cleaning and regular maintenance.",
            content="<p>Regular cleaning keeps your home tidy; deep cleaning targets hidden dirt and buildup.</p>",
            category="Residential",
            published=True,
            published_at=timezone.now(),
        )

        for slug in ["summer-cleaning-adelaide", "deep-cleaning-vs-regular-cleaning"]:
            with self.subTest(slug=slug):
                response = self.client.get(f"/blog/{slug}/")
                self.assertEqual(response.status_code, 200)
