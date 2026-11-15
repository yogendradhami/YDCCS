from types import SimpleNamespace
from unittest.mock import patch

import fitz
from django.test import RequestFactory, SimpleTestCase

from reports.pdf_utils import generate_cleaning_report_pdf
from reports.views import download_cleaning_report_pdf


class EmptyPhotoQuerySet:
    def filter(self, **kwargs):
        return self

    def order_by(self, *args):
        return self

    def exists(self):
        return False

    def first(self):
        return None

    def __iter__(self):
        return iter(())


class CleaningReportPdfTests(SimpleTestCase):
    @staticmethod
    def make_booking():
        return SimpleNamespace(
            id=18,
            pk=18,
            booking_date=None,
            booking_time=None,
            get_service_type_display=lambda: "Carpet Cleaning",
            get_status_display=lambda: "Completed",
            address="6 Melrose Avenue",
            suburb_postcode="Clearview 5085",
            customer=None,
            assigned_employees=SimpleNamespace(all=lambda: []),
            assigned_employee=None,
            quoted_price="120.00",
            notes="Service completed.",
            job_photos=EmptyPhotoQuerySet(),
        )

    def test_download_has_watermark_on_each_page_and_aligned_header(self):
        booking = self.make_booking()
        booking.customer = SimpleNamespace(
            full_name="Example Customer",
            phone="0400000000",
            email="customer@example.com",
        )
        request = RequestFactory().get("/reports/18/download/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_staff=True,
            is_superuser=False,
        )

        with patch("reports.views.get_object_or_404", return_value=booking):
            response = download_cleaning_report_pdf(request, booking_id=18)

        pdf_bytes = b"".join(response.streaming_content)
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        self.assertGreater(len(document), 1)

        for page in document:
            self.assertIn("YD COMMERCIAL CLEANING SERVICES", page.get_text())

        first_page = document[0]
        words = first_page.get_text("words")
        generated = next(word for word in words if word[4] == "GENERATED")
        company_name = next(word for word in words if word[4] == "Commercial")
        self.assertLess(company_name[0], generated[0])
        self.assertLess(generated[1], first_page.rect.height * 0.2)
        self.assertIn("GENERATED DATE & TIME", first_page.get_text())
        self.assertIn("CLEANING COMPLETION REPORT", first_page.get_text())
        self.assertTrue(first_page.get_images())

    def test_emailed_report_has_watermarks_and_brand_header_on_each_page(self):
        pdf_bytes = generate_cleaning_report_pdf(self.make_booking()).getvalue()
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        self.assertGreater(len(document), 1)

        for page in document:
            self.assertIn("YD COMMERCIAL CLEANING SERVICES", page.get_text())

        first_page = document[0]
        words = first_page.get_text("words")
        generated = next(word for word in words if word[4] == "GENERATED")
        company_name = next(word for word in words if word[4] == "YD")
        self.assertLess(company_name[0], generated[0])
        self.assertLess(generated[1], first_page.rect.height * 0.2)
        self.assertIn("GENERATED DATE & TIME", first_page.get_text())
        self.assertIn("Report reference: YD-000018", first_page.get_text())
        self.assertTrue(first_page.get_images())
