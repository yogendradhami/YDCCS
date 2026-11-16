import csv
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from scripts.seo_indexing_audit import (
    PageMetadataParser,
    load_csv_urls,
    normalize_url,
    robots_disallows,
)


class SeoAuditScriptTests(SimpleTestCase):
    def test_metadata_parser_reads_indexing_and_internal_link_fields(self):
        parser = PageMetadataParser()
        parser.feed(
            '<html><head><title> Adelaide Cleaning </title>'
            '<meta name="description" content="A useful description">'
            '<meta name="robots" content="index, follow">'
            '<link rel="canonical" href="https://www.example.test/page/">'
            '</head><body><a href="/contact/">Contact</a></body></html>'
        )

        self.assertEqual(parser.title.strip(), "Adelaide Cleaning")
        self.assertEqual(parser.description, "A useful description")
        self.assertEqual(parser.robots, ["index, follow"])
        self.assertEqual(
            parser.canonical,
            "https://www.example.test/page/",
        )
        self.assertEqual(parser.internal_links, ["/contact/"])

    def test_normalization_removes_fragments_and_robots_rules_respect_allow(self):
        self.assertEqual(
            normalize_url("https://www.example.test/page/#section"),
            "https://www.example.test/page/",
        )
        rules = [
            ("disallow", "/booking/"),
            ("disallow", "/private/"),
            ("allow", "/private/public-guide/"),
        ]
        self.assertTrue(
            robots_disallows("https://www.example.test/booking/", rules)
        )
        self.assertFalse(
            robots_disallows(
                "https://www.example.test/private/public-guide/", rules
            )
        )

    def test_gsc_csv_url_column_is_imported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "gsc-export.csv"
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Page", "Clicks", "Impressions"])
                writer.writerow(["https://www.example.test/a/", "1", "5"])
                writer.writerow(["https://www.example.test/b/", "0", "2"])

            self.assertEqual(
                load_csv_urls(path),
                [
                    "https://www.example.test/a/",
                    "https://www.example.test/b/",
                ],
            )
