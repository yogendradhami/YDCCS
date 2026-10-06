from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from employees.models import Employee

from .models import CompanyDocument, ComplianceRequirement
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
