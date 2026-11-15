"""Shared branding helpers for generated PDF documents."""

from reportlab.pdfgen.canvas import Canvas


def draw_company_watermark(pdf_canvas, document):
    """Draw a subtle, diagonal company-name watermark over page content."""
    page_width, page_height = getattr(document, "pagesize", document)

    pdf_canvas.saveState()
    pdf_canvas.setFillColorRGB(11 / 255, 44 / 255, 36 / 255)
    pdf_canvas.setFillAlpha(0.08)
    pdf_canvas.translate(page_width / 2, page_height / 2)
    pdf_canvas.rotate(32)
    pdf_canvas.setFont("Helvetica-Bold", 24)
    pdf_canvas.drawCentredString(0, 0, "YD COMMERCIAL CLEANING SERVICES")
    pdf_canvas.restoreState()


class CompanyWatermarkCanvas(Canvas):
    """Apply the company watermark over the content on every completed page."""

    def showPage(self):
        draw_company_watermark(self, self._pagesize)
        super().showPage()
