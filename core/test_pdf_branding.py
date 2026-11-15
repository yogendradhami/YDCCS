from io import BytesIO

import fitz
from django.test import SimpleTestCase
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet

from core.pdf_branding import CompanyWatermarkCanvas, draw_company_watermark


class CompanyWatermarkTests(SimpleTestCase):
    def test_draws_company_name_on_pdf_canvas(self):
        buffer = BytesIO()
        pdf_canvas = Canvas(buffer, pagesize=A4, pageCompression=0)

        draw_company_watermark(pdf_canvas, A4)
        pdf_canvas.save()

        self.assertIn(b"YD COMMERCIAL CLEANING SERVICES", buffer.getvalue())

    def test_company_canvas_watermarks_every_page_after_page_content(self):
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()

        document.build(
            [
                Paragraph("Page one content", styles["BodyText"]),
                PageBreak(),
                Paragraph("Page two content", styles["BodyText"]),
            ],
            canvasmaker=CompanyWatermarkCanvas,
        )

        pdf = fitz.open(stream=buffer.getvalue(), filetype="pdf")
        self.assertEqual(len(pdf), 2)
        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text()
            self.assertIn(
                f"Page {'one' if page_number == 1 else 'two'} content",
                page_text,
            )
            self.assertIn("YD COMMERCIAL CLEANING SERVICES", page_text)
