from django.test import SimpleTestCase

from .templatetags.seo_tags import cloudinary_optimize


class CloudinaryImageOptimizationTests(SimpleTestCase):
    def test_cloudinary_image_gets_responsive_delivery_transform(self):
        url = "https://res.cloudinary.com/example/image/upload/sample.jpg"
        self.assertEqual(
            cloudinary_optimize(url, 800),
            "https://res.cloudinary.com/example/image/upload/f_auto,q_auto,c_limit,w_800/sample.jpg",
        )

    def test_non_cloudinary_and_raw_assets_are_not_rewritten(self):
        lookalike = "https://evilres.cloudinary.com/example/image/upload/sample.jpg"
        raw = "https://res.cloudinary.com/example/raw/upload/report.pdf"
        self.assertEqual(cloudinary_optimize(lookalike), lookalike)
        self.assertEqual(cloudinary_optimize(raw), raw)
