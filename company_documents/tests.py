from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
import requests

from core.test_utils import grant_dashboard_permissions
from employees.models import Employee

from .models import (
    BulkImportBatch,
    BulkImportItem,
    CompanyDocument,
    ComplianceRequirement,
)
from .services.compliance_requirements import evaluate_requirement
from .services.compliance_resolution import resolve_document_compliance
from .services.bulk_import import (
    analyse_item,
    create_batch,
    get_staged_file_for_extraction,
)


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
        grant_dashboard_permissions(
            self.user,
            "company_documents.view_companydocument",
            "company_documents.change_companydocument",
        )
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
        grant_dashboard_permissions(
            self.staff,
            "company_documents.view_bulkimportbatch",
            "company_documents.delete_bulkimportbatch",
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


class BulkImportUploadSafetyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bulk-upload-admin")

    @staticmethod
    def pdf(name):
        return SimpleUploadedFile(name, b"%PDF-1.4 sample", content_type="application/pdf")

    @patch("company_documents.services.bulk_import.cloudinary.uploader.upload")
    def test_documents_are_staged_as_raw_resources(self, upload):
        upload.side_effect = lambda uploaded, **_kwargs: {
            "public_id": f"company_document_staging/{uploaded.name}",
            "resource_type": "raw",
        }

        batch = create_batch(self.user, [self.pdf("one.pdf"), self.pdf("two.pdf")])

        self.assertEqual(batch.items.count(), 2)
        self.assertTrue(all(item.staging_file.name for item in batch.items.all()))
        self.assertTrue(all(call.kwargs["resource_type"] == "raw" for call in upload.call_args_list))

    @patch("company_documents.services.bulk_import.requests.get")
    @patch("company_documents.services.bulk_import.private_download_url")
    def test_staged_raw_document_download_uses_signed_delivery_url(
        self, private_download_url, get
    ):
        private_download_url.return_value = (
            "https://api.cloudinary.com/v1_1/example/raw/download?signature=signed"
        )
        response = get.return_value
        response.content = b"%PDF-1.4 invoice"

        batch = BulkImportBatch.objects.create(
            batch_reference="SIGNED-DOWNLOAD",
            uploaded_by=self.user,
            total_files=1,
        )
        item = BulkImportItem.objects.create(
            batch=batch,
            original_filename="invoice.pdf",
            staging_file="company_document_staging/2026/10/invoice.pdf",
        )

        downloaded = get_staged_file_for_extraction(item)

        private_download_url.assert_called_once_with(
            "company_document_staging/2026/10/invoice",
            "pdf",
            resource_type="raw",
            type="upload",
            expires_at=private_download_url.call_args.kwargs["expires_at"],
            attachment=True,
            cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
            api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
            api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
        )
        get.assert_called_once_with(
            private_download_url.return_value,
            timeout=60,
            allow_redirects=True,
        )
        self.assertEqual(downloaded.read(), b"%PDF-1.4 invoice")
        self.assertEqual(downloaded.name, "invoice.pdf")

    @patch("company_documents.services.bulk_import.requests.get")
    @patch("company_documents.services.bulk_import.private_download_url")
    def test_analysis_reports_sanitized_cloudinary_401_for_retry(
        self, private_download_url, get
    ):
        private_download_url.return_value = (
            "https://api.cloudinary.com/private-signed-download"
        )
        response = get.return_value
        response.status_code = 401
        response.raise_for_status.side_effect = requests.HTTPError(
            "401 Client Error: Unauthorized for url: "
            "https://api.cloudinary.com/private-signed-download?signature=secret",
            response=response,
        )

        batch = BulkImportBatch.objects.create(
            batch_reference="SIGNED-401",
            uploaded_by=self.user,
            total_files=1,
        )
        item = BulkImportItem.objects.create(
            batch=batch,
            original_filename="invoice.pdf",
            staging_file="company_document_staging/2026/10/invoice.pdf",
        )

        with self.assertRaises(requests.HTTPError):
            analyse_item(item)

        item.refresh_from_db()
        self.assertEqual(item.status, BulkImportItem.Status.FAILED)
        self.assertIn("HTTP 401", item.error_message)
        self.assertNotIn("api.cloudinary.com", item.error_message)
        self.assertNotIn("signature=secret", item.error_message)

    @patch("company_documents.services.bulk_import._cleanup_staging_assets")
    @patch("company_documents.services.bulk_import.cloudinary.uploader.upload")
    def test_partial_stage_failure_cleans_assets_and_marks_batch_failed(
        self, upload, cleanup
    ):
        def upload_side_effect(uploaded, **_kwargs):
            if uploaded.name == "bad.pdf":
                raise RuntimeError("Cloudinary unavailable")
            return {
                "public_id": "company_document_staging/good.pdf",
                "resource_type": "raw",
            }

        upload.side_effect = upload_side_effect
        with self.assertRaises(RuntimeError):
            create_batch(self.user, [self.pdf("good.pdf"), self.pdf("bad.pdf")])

        batch = BulkImportBatch.objects.get(uploaded_by=self.user)
        self.assertEqual(batch.status, BulkImportBatch.Status.FAILED)
        self.assertEqual(batch.items.filter(status=BulkImportItem.Status.FAILED).count(), 2)
        cleanup.assert_called_once_with(["company_document_staging/good.pdf"])

    @patch("company_documents.services.bulk_import.cloudinary.uploader.upload")
    def test_unsupported_file_type_is_rejected_before_batch_creation(self, upload):
        with self.assertRaises(ValueError):
            create_batch(
                self.user,
                [SimpleUploadedFile("payload.exe", b"not allowed")],
            )

        self.assertEqual(BulkImportBatch.objects.count(), 0)
        upload.assert_not_called()
