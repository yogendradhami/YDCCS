from datetime import date
from decimal import Decimal
from unittest.mock import patch

import fitz
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from dashboard.models import CleaningSupply, PurchaseOrder, Supplier
from expenses.models import Expense

from .models import CompanyDocument, CompanyDocumentAudit, InvoiceDocumentReview
from .services.document_extractor import extract_text
from .services.invoice_review import (
    build_purchase_order_reconciliation,
    create_invoice_review,
    extract_invoice_fields,
    verify_invoice_review,
)
from .services.invoice_review import post_verified_invoice_review


INVOICE_TEXT = """Acme Cleaning Supplies
Supplier: Acme Cleaning Supplies
Invoice Number: AC-2026-7
Invoice Date: 01/10/2026
Due Date: 31/10/2026
Description: Cleaning products
Subtotal: $100.00
GST: $10.00
Total: $110.00
Cleaning chemical 2 $50.00 $100.00
Amount due: $110.00
"""


class InvoiceExtractionTests(SimpleTestCase):
    def test_extracts_invoice_fields_and_decimal_line_items(self):
        parsed = extract_invoice_fields(INVOICE_TEXT, method="pdf")

        self.assertEqual(parsed["data"]["supplier_name"], "Acme Cleaning Supplies")
        self.assertEqual(parsed["data"]["invoice_number"], "AC-2026-7")
        self.assertEqual(parsed["data"]["invoice_date"], "2026-10-01")
        self.assertEqual(parsed["data"]["due_date"], "2026-10-31")
        self.assertEqual(parsed["data"]["subtotal"], "100.00")
        self.assertEqual(parsed["data"]["gst"], "10.00")
        self.assertEqual(parsed["data"]["total"], "110.00")
        self.assertEqual(parsed["data"]["payment_status"], "unpaid_claimed")
        self.assertEqual(
            parsed["data"]["line_items"][0],
            {
                "description": "Cleaning chemical",
                "quantity": "2",
                "unit_price": "50.00",
                "line_total": "100.00",
            },
        )
        self.assertEqual(parsed["validation_errors"], [])

    def test_flags_totals_and_date_validation_errors(self):
        parsed = extract_invoice_fields(
            "Invoice Date: 31/10/2026\n"
            "Due Date: 01/10/2026\n"
            "Subtotal: $100.00\nGST: $10.00\nTotal: $120.00",
            method="pdf",
        )

        self.assertIn(
            "The due date is earlier than the invoice date.",
            parsed["validation_errors"],
        )
        self.assertIn(
            "Subtotal plus GST does not match the extracted total.",
            parsed["validation_errors"],
        )

    def test_ocr_confidence_is_reduced_and_extraction_error_is_retained(self):
        parsed = extract_invoice_fields(
            INVOICE_TEXT,
            method="image_ocr",
            extraction_error="OCR timed out.",
        )

        self.assertLess(parsed["confidence"]["total"], 0.88)
        self.assertIn("OCR timed out.", parsed["validation_errors"])

    @override_settings(COMPANY_DOCUMENT_OCR_MAX_PAGES=2)
    @patch("company_documents.services.document_extractor._run_tesseract")
    def test_scanned_pdf_uses_configured_local_ocr_adapter(self, mock_ocr):
        mock_ocr.return_value = "Invoice Number: SCAN-1"
        pdf = fitz.open()
        pdf.new_page(width=200, height=100)
        uploaded_file = SimpleUploadedFile(
            "scan.pdf",
            pdf.tobytes(),
            content_type="application/pdf",
        )
        pdf.close()

        extracted = extract_text(uploaded_file)

        self.assertEqual(extracted["method"], "pdf_ocr")
        self.assertEqual(extracted["text"], "Invoice Number: SCAN-1")
        mock_ocr.assert_called_once()


class InvoiceReviewServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="invoice-reviewer")
        self.supplier = Supplier.objects.create(name="Acme Cleaning Supplies")

    def create_document(self, name):
        return CompanyDocument.objects.create(
            name=name,
            category=CompanyDocument.Category.FINANCE,
            document_type="Supplier Invoice",
            related_type=CompanyDocument.RelatedType.SUPPLIER,
            supplier=self.supplier,
            file="company_documents/invoice.pdf",
            original_filename="invoice.pdf",
            uploaded_by=self.user,
        )

    def upload(self):
        return SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-1.7\ninvoice",
            content_type="application/pdf",
        )

    def verified_data(self):
        return {
            "supplier": self.supplier,
            "supplier_name": self.supplier.name,
            "abn": "",
            "invoice_number": "AC-2026-7",
            "invoice_date": date(2026, 10, 1),
            "due_date": date(2026, 10, 31),
            "description": "Cleaning products",
            "line_items_json": [
                {
                    "description": "Cleaning chemical",
                    "quantity": "2",
                    "unit_price": "50.00",
                    "line_total": "100.00",
                }
            ],
            "subtotal": Decimal("100.00"),
            "gst": Decimal("10.00"),
            "total": Decimal("110.00"),
        }

    @patch("company_documents.services.invoice_review.extract_text")
    def test_invoice_review_is_pending_and_duplicate_is_suggested(self, mock_extract):
        mock_extract.return_value = {
            "text": INVOICE_TEXT,
            "method": "pdf",
            "error": "",
        }
        first = self.create_document("Acme October invoice")
        second = self.create_document("Acme replacement invoice")

        first_review, first_created = create_invoice_review(first, self.upload())
        second_review, second_created = create_invoice_review(second, self.upload())

        self.assertTrue(first_created)
        self.assertTrue(second_created)
        self.assertEqual(first_review.status, InvoiceDocumentReview.Status.PENDING)
        self.assertEqual(first_review.suggested_supplier, self.supplier)
        self.assertEqual(second_review.duplicate_of, first_review)
        self.assertTrue(
            any("Possible duplicate" in error for error in second_review.validation_errors)
        )
        self.assertEqual(CompanyDocumentAudit.objects.count(), 0)

    def test_verified_supplier_invoice_number_cannot_be_reused(self):
        review, _ = InvoiceDocumentReview.objects.get_or_create(
            document=self.create_document("First invoice"),
            defaults={
                "normalized_invoice_number": "AC20267",
                "status": InvoiceDocumentReview.Status.VERIFIED,
                "supplier": self.supplier,
            },
        )
        duplicate_document = self.create_document("Duplicate invoice")
        duplicate_review = InvoiceDocumentReview.objects.create(
            document=duplicate_document,
        )

        with self.assertRaises(ValidationError):
            verify_invoice_review(
                review_id=duplicate_review.pk,
                actor=self.user,
                verified_data={
                    "supplier": self.supplier,
                    "supplier_name": self.supplier.name,
                    "abn": "",
                    "invoice_number": "AC-2026-7",
                    "invoice_date": date(2026, 10, 1),
                    "due_date": None,
                    "description": "Cleaning products",
                    "line_items_json": [],
                    "subtotal": Decimal("100.00"),
                    "gst": Decimal("10.00"),
                    "total": Decimal("110.00"),
                },
            )

        review.refresh_from_db()
        duplicate_review.refresh_from_db()
        self.assertEqual(review.status, InvoiceDocumentReview.Status.VERIFIED)
        self.assertEqual(duplicate_review.status, InvoiceDocumentReview.Status.PENDING)
        self.assertFalse(CompanyDocumentAudit.objects.exists())

    def test_approval_posts_expense_once_without_marking_paid_or_receiving_stock(self):
        document = self.create_document("Acme October invoice")
        review = InvoiceDocumentReview.objects.create(
            document=document,
            suggested_expense_category="cleaning_supplies",
        )
        verify_invoice_review(
            review_id=review.pk,
            actor=self.user,
            verified_data=self.verified_data(),
        )
        supply = CleaningSupply.objects.create(
            name="Cleaning chemical",
            current_stock=4,
            minimum_stock=2,
            supplier_name=self.supplier.name,
        )
        order = PurchaseOrder.objects.create(
            supply=supply,
            supplier_name=self.supplier.name,
            quantity=10,
            quantity_received=1,
            unit_cost=Decimal("50.00"),
            status="ordered",
        )

        expense, created = post_verified_invoice_review(
            review_id=review.pk,
            actor=self.user,
            expense_category="cleaning_supplies",
            purchase_order_id=order.pk,
        )
        repeated_expense, repeated_created = post_verified_invoice_review(
            review_id=review.pk,
            actor=self.user,
            expense_category="cleaning_supplies",
            purchase_order_id=order.pk,
        )

        review.refresh_from_db()
        supply.refresh_from_db()
        reconciliation = build_purchase_order_reconciliation(review)
        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(expense.pk, repeated_expense.pk)
        self.assertEqual(expense.amount, Decimal("110.00"))
        self.assertEqual(expense.gst_amount, Decimal("10.00"))
        self.assertEqual(expense.supplier, self.supplier)
        self.assertEqual(expense.purchase_order, order)
        self.assertEqual(review.suggested_purchase_order, order)
        self.assertEqual(reconciliation["invoice_quantity"], Decimal("2"))
        self.assertEqual(reconciliation["received_quantity"], 1)
        self.assertEqual(reconciliation["invoice_vs_received"], Decimal("1"))
        self.assertEqual(expense.invoice_number, "AC-2026-7")
        self.assertEqual(expense.recorded_by, self.user)
        self.assertIsNone(expense.paid_by)
        self.assertEqual(
            expense.payment_status,
            Expense.PaymentStatus.UNCONFIRMED,
        )
        self.assertEqual(review.status, InvoiceDocumentReview.Status.APPROVED)
        self.assertEqual(supply.current_stock, 4)
        self.assertEqual(Expense.objects.filter(invoice_review=review).count(), 1)

    def test_invoice_approval_page_posts_verified_expense(self):
        manager = User.objects.create_superuser(
            username="invoice-posting-manager",
            email="posting-manager@example.com",
            password="test-password",
        )
        document = self.create_document("Acme October invoice")
        review = InvoiceDocumentReview.objects.create(document=document)
        verify_invoice_review(
            review_id=review.pk,
            actor=manager,
            verified_data=self.verified_data(),
        )
        self.client.force_login(manager)

        response = self.client.post(
            reverse(
                "company_documents:invoice_review_approve",
                kwargs={"review_id": review.pk},
            ),
            {"category": "cleaning_supplies", "purchase_order": ""},
        )

        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(invoice_review=review)
        self.assertEqual(expense.amount, Decimal("110.00"))
        self.assertEqual(expense.gst_amount, Decimal("10.00"))
        self.assertIsNone(expense.paid_by)

    def test_invoice_review_detail_renders_for_authorised_manager(self):
        manager = User.objects.create_superuser(
            username="invoice-manager",
            email="manager@example.com",
            password="test-password",
        )
        document = self.create_document("Acme October invoice")
        review = InvoiceDocumentReview.objects.create(
            document=document,
            extracted_data=extract_invoice_fields(INVOICE_TEXT)["data"],
            confidence={"total": 0.88},
        )
        self.client.force_login(manager)

        response = self.client.get(
            reverse(
                "company_documents:invoice_review_detail",
                kwargs={"review_id": review.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check and verify details")
        self.assertContains(response, "0.88")

    @patch("company_documents.services.invoice_review.extract_text")
    @patch(
        "company_documents.views.upload_raw_document",
        return_value="company_documents/uploaded-invoice.pdf",
    )
    def test_existing_document_upload_creates_pending_review(
        self,
        _mock_upload,
        mock_extract,
    ):
        manager = User.objects.create_superuser(
            username="invoice-uploader",
            email="uploader@example.com",
            password="test-password",
        )
        mock_extract.return_value = {
            "text": INVOICE_TEXT,
            "method": "pdf",
            "error": "",
        }
        self.client.force_login(manager)

        response = self.client.post(
            reverse("company_documents:upload"),
            {
                "name": "Acme invoice",
                "category": CompanyDocument.Category.FINANCE,
                "document_type": "Supplier Invoice",
                "related_type": CompanyDocument.RelatedType.COMPANY,
                "file": self.upload(),
            },
        )

        self.assertEqual(response.status_code, 302)
        review = InvoiceDocumentReview.objects.get()
        self.assertEqual(review.status, InvoiceDocumentReview.Status.PENDING)
        self.assertEqual(review.extracted_data["invoice_number"], "AC-2026-7")
        self.assertFalse(CompanyDocumentAudit.objects.filter(
            metadata__event="invoice_document_verified"
        ).exists())

    @patch("company_documents.services.invoice_review.extract_text")
    @patch(
        "company_documents.views.upload_raw_document",
        return_value="company_documents/replaced-invoice.pdf",
    )
    def test_replacing_invoice_preserves_review_on_archived_version(
        self,
        _mock_upload,
        mock_extract,
    ):
        manager = User.objects.create_superuser(
            username="invoice-version-manager",
            email="version-manager@example.com",
            password="test-password",
        )
        mock_extract.return_value = {
            "text": INVOICE_TEXT,
            "method": "pdf",
            "error": "",
        }
        document = self.create_document("Acme invoice")
        previous_review = InvoiceDocumentReview.objects.create(
            document=document,
            extracted_data={"invoice_number": "AC-2026-7"},
        )
        self.client.force_login(manager)

        response = self.client.post(
            reverse("company_documents:edit", kwargs={"pk": document.pk}),
            {
                "name": document.name,
                "category": CompanyDocument.Category.FINANCE,
                "document_type": document.document_type,
                "description": document.description,
                "document_reference": document.document_reference,
                "related_type": CompanyDocument.RelatedType.SUPPLIER,
                "supplier": self.supplier.pk,
                "issue_date": "",
                "expiry_date": "",
                "review_date": "",
                "is_sensitive": "",
                "file": self.upload(),
            },
        )

        document.refresh_from_db()
        previous_review.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(previous_review.document_id, document.previous_version_id)
        self.assertTrue(
            InvoiceDocumentReview.objects.filter(
                document=document,
                status=InvoiceDocumentReview.Status.PENDING,
            ).exists()
        )
