from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from employees.models import Employee

from .models import (
    BulkImportBatch,
    BulkImportItem,
    CompanyDocument,
    ComplianceRequirement,
)
from .services.compliance_requirements import evaluate_requirement
from .services.compliance_resolution import resolve_document_compliance


class ComplianceResolutionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("document-admin")
        self.employee = Employee.objects.create(
            full_name="Jordan Lee",
            phone="0400123456",
            email="jordan@example.com",
        )
        self.requirement = ComplianceRequirement.objects.create(
            name="Employment Agreement",
            scope=ComplianceRequirement.Scope.EMPLOYEE,
            category=CompanyDocument.Category.EMPLOYEE,
            document_type="Employment Agreement",
            required=True,
            active=True,
        )

    def create_document(self, **overrides):
        data = {
            "name": "Employment Agreement",
            "category": CompanyDocument.Category.EMPLOYEE,
            "document_type": "Employment Agreement",
            "related_type": CompanyDocument.RelatedType.EMPLOYEE,
            "employee": self.employee,
            "file": "company_documents/test.pdf",
            "original_filename": "test.pdf",
            "uploaded_by": self.user,
            "status": CompanyDocument.Status.ACTIVE,
        }
        data.update(overrides)
        return CompanyDocument.objects.create(**data)

    def test_current_active_replacement_satisfies_requirement(self):
        today = timezone.localdate()
        expired_document = self.create_document(
            expiry_date=today - timedelta(days=1),
            version=1,
        )
        renewed_document = self.create_document(
            expiry_date=today + timedelta(days=365),
            version=2,
            previous_version=expired_document,
        )

        result = evaluate_requirement(
            self.requirement,
            entity=self.employee,
        )

        self.assertEqual(result.status, "satisfied")
        self.assertEqual(result.document, renewed_document)

    def test_resolution_reports_not_applicable_without_matching_requirement(self):
        document = self.create_document(
            document_type="Other Document",
        )

        resolution = resolve_document_compliance(document)

        self.assertEqual(resolution["status"], "not_applicable")
        self.assertEqual(list(resolution["results"]), [])

    def test_document_health_properties_are_available(self):
        document = self.create_document(
            expiry_date=timezone.localdate() + timedelta(days=90),
        )

        self.assertEqual(document.health_status, "healthy")
        self.assertEqual(document.health_status_label, "Healthy")
        self.assertEqual(document.related_object, self.employee)
        self.assertEqual(document.related_name, self.employee.full_name)

    @patch("company_documents.views.upload_raw_document")
    def test_replacing_file_keeps_current_record_and_links_previous_version(
        self,
        mock_upload_raw_document,
    ):
        mock_upload_raw_document.return_value = "company_documents/new-file.pdf"
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        today = timezone.localdate()
        document = self.create_document(
            expiry_date=today - timedelta(days=1),
            review_date=today - timedelta(days=1),
            version=1,
        )
        replacement_file = SimpleUploadedFile(
            "renewed.pdf",
            b"renewed document",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse(
                "company_documents:edit",
                kwargs={"pk": document.pk},
            ),
            {
                "name": document.name,
                "category": document.category,
                "document_type": document.document_type,
                "description": document.description,
                "document_reference": document.document_reference,
                "related_type": document.related_type,
                "employee": self.employee.pk,
                "issue_date": today.isoformat(),
                "expiry_date": (today + timedelta(days=365)).isoformat(),
                "review_date": (today + timedelta(days=180)).isoformat(),
                "file": replacement_file,
            },
        )

        document.refresh_from_db()
        previous_document = document.previous_version

        self.assertRedirects(
            response,
            reverse(
                "company_documents:detail",
                kwargs={"pk": document.pk},
            ),
        )
        self.assertEqual(CompanyDocument.objects.count(), 2)
        self.assertEqual(document.version, 2)
        self.assertEqual(document.file.name, "company_documents/new-file.pdf")
        self.assertEqual(document.expiry_date, today + timedelta(days=365))
        self.assertEqual(document.status, CompanyDocument.Status.ACTIVE)
        self.assertIsNotNone(previous_document)
        self.assertNotEqual(previous_document.pk, document.pk)
        self.assertEqual(previous_document.version, 1)
        self.assertEqual(previous_document.status, CompanyDocument.Status.ARCHIVED)
        self.assertEqual(previous_document.expiry_date, today - timedelta(days=1))


class BulkImportHistoryTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="document-manager",
            password="test-password",
            is_staff=True,
        )
        self.uploader = User.objects.create_user(
            username="jlee",
            first_name="Jordan",
            last_name="Lee",
        )
        self.client.force_login(self.staff)

    def create_batch(
        self,
        reference,
        status=BulkImportBatch.Status.UPLOADED,
        uploader=None,
        created_at=None,
    ):
        batch = BulkImportBatch.objects.create(
            batch_reference=reference,
            status=status,
            uploaded_by=uploader or self.uploader,
        )
        if created_at:
            BulkImportBatch.objects.filter(pk=batch.pk).update(
                created_at=created_at
            )
        return batch

    def get_batches(self, **params):
        response = self.client.get(
            reverse("company_documents:bulk_import_list"),
            params,
        )
        self.assertEqual(response.status_code, 200)
        return response.context["batches"]

    def test_bulk_import_history_requires_staff_access(self):
        url = reverse("company_documents:bulk_import_list")
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

        nonstaff = User.objects.create_user(
            username="document-viewer",
            password="test-password",
        )
        self.client.force_login(nonstaff)
        self.assertIn(self.client.get(url).status_code, {302, 403})

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_search_filters_by_batch_reference(self):
        matching = self.create_batch("IMP-2026-ALPHA")
        self.create_batch("OTHER-2026")

        batches = self.get_batches(q="alpha")

        self.assertEqual(list(batches), [matching])

    def test_search_filters_by_uploader_username_and_name(self):
        matching = self.create_batch("UPLOADER-MATCH")
        self.create_batch(
            "OTHER-UPLOADER",
            uploader=User.objects.create_user(username="someone-else"),
        )

        for query in ("jlee", "Jordan", "Lee"):
            with self.subTest(query=query):
                self.assertEqual(
                    list(self.get_batches(q=query)),
                    [matching],
                )

    def test_status_filter_uses_batch_status(self):
        matching = self.create_batch(
            "COMPLETED-BATCH",
            status=BulkImportBatch.Status.COMPLETED,
        )
        self.create_batch("UPLOADED-BATCH")

        self.assertEqual(
            list(self.get_batches(status=BulkImportBatch.Status.COMPLETED)),
            [matching],
        )

    def test_date_from_and_date_to_filters_are_inclusive(self):
        today = timezone.localdate()
        before = self.create_batch("DATE-BEFORE")
        matching = self.create_batch("DATE-MATCH")
        after = self.create_batch("DATE-AFTER")
        BulkImportBatch.objects.filter(pk=before.pk).update(
            created_at=timezone.now() - timedelta(days=4)
        )
        BulkImportBatch.objects.filter(pk=matching.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )
        BulkImportBatch.objects.filter(pk=after.pk).update(
            created_at=timezone.now()
        )

        batches = self.get_batches(
            date_from=(today - timedelta(days=2)).isoformat(),
            date_to=(today - timedelta(days=2)).isoformat(),
        )

        self.assertEqual(list(batches), [matching])

    def test_invalid_dates_are_ignored_without_failing(self):
        batch = self.create_batch("SAFE-INVALID-DATE")

        batches = self.get_batches(date_from="not-a-date", date_to="2026-99-99")

        self.assertEqual(list(batches), [batch])

    def test_pagination_preserves_active_filters(self):
        for index in range(16):
            self.create_batch(
                f"PAGE-BATCH-{index:02}",
                status=BulkImportBatch.Status.COMPLETED,
            )

        date_from = timezone.localdate().isoformat()
        response = self.client.get(
            reverse("company_documents:bulk_import_list"),
            {
                "page": 1,
                "q": "PAGE",
                "status": BulkImportBatch.Status.COMPLETED,
                "date_from": date_from,
                "date_to": date_from,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 16)
        self.assertContains(
            response,
            f"q=PAGE&amp;status=completed&amp;date_from={date_from}"
            f"&amp;date_to={date_from}&amp;page=2",
        )

    def test_delete_requires_post(self):
        batch = self.create_batch("POST-ONLY")

        response = self.client.get(
            reverse(
                "company_documents:bulk_import_delete",
                kwargs={"pk": batch.pk},
            )
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(BulkImportBatch.objects.filter(pk=batch.pk).exists())

    @patch("company_documents.views.delete_staged_raw_document")
    def test_delete_removes_batch_items_and_preserves_company_documents(
        self,
        mock_delete_staged_raw_document,
    ):
        batch = self.create_batch("DELETE-STAGING-ONLY")
        document = CompanyDocument.objects.create(
            name="Permanent document",
            category=CompanyDocument.Category.COMPANY,
            document_type="Policy",
            related_type=CompanyDocument.RelatedType.COMPANY,
            file="company_documents/permanent.pdf",
            original_filename="permanent.pdf",
            uploaded_by=self.staff,
        )
        item = BulkImportItem.objects.create(
            batch=batch,
            original_filename="staged.pdf",
            staging_file="company_document_staging/staged.pdf",
            imported_document=document,
        )

        response = self.client.post(
            reverse(
                "company_documents:bulk_import_delete",
                kwargs={"pk": batch.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse("company_documents:bulk_import_list"),
        )
        self.assertFalse(
            BulkImportBatch.objects.filter(pk=batch.pk).exists()
        )
        self.assertFalse(
            BulkImportItem.objects.filter(pk=item.pk).exists()
        )
        self.assertTrue(
            CompanyDocument.objects.filter(pk=document.pk).exists()
        )
        mock_delete_staged_raw_document.assert_called_once_with(item)

    @patch("company_documents.views.delete_staged_raw_document")
    def test_delete_is_blocked_while_batch_is_processing(
        self,
        mock_delete_staged_raw_document,
    ):
        for status in (
            BulkImportBatch.Status.ANALYSING,
            BulkImportBatch.Status.IMPORTING,
        ):
            with self.subTest(status=status):
                batch = self.create_batch(
                    f"PROCESSING-{status}",
                    status=status,
                )
                item = BulkImportItem.objects.create(
                    batch=batch,
                    original_filename="staged.pdf",
                    staging_file="company_document_staging/staged.pdf",
                )

                response = self.client.post(
                    reverse(
                        "company_documents:bulk_import_delete",
                        kwargs={"pk": batch.pk},
                    )
                )

                self.assertRedirects(
                    response,
                    reverse("company_documents:bulk_import_list"),
                )
                self.assertTrue(
                    BulkImportBatch.objects.filter(pk=batch.pk).exists()
                )
                self.assertTrue(
                    BulkImportItem.objects.filter(pk=item.pk).exists()
                )

        mock_delete_staged_raw_document.assert_not_called()
