import json
from datetime import date, time
from unittest.mock import patch

from cloudinary.utils import api_sign_request
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from bookings.models import Booking, JobPhoto
from customers.models import Customer
from employees.models import Employee
from induction.models import EmployeeInduction, InductionProgramme


@override_settings(
    CLOUDINARY_STORAGE={
        "CLOUD_NAME": "test-cloud",
        "API_KEY": "test-key",
        "API_SECRET": "test-secret",
    }
)
class JobPhotoDirectUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("employee", password="test-password")
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Test Employee",
            phone="0400000000",
        )
        programme = InductionProgramme.objects.create(name="Upload test induction")
        EmployeeInduction.objects.create(
            employee=self.employee,
            programme=programme,
            status="completed",
        )
        self.customer = Customer.objects.create(
            full_name="Test Customer",
            email="customer@example.com",
            phone="0400000001",
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            service_type="House Cleaning",
            booking_date=date(2026, 10, 20),
            booking_time=time(9, 0),
            address="1 Test Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.employee,
        )
        self.client.force_login(self.user)
        self.url = reverse("upload_job_photo", args=[self.booking.pk])

    def _signed_receipt(self, public_id, *, version=123):
        return {
            "public_id": public_id,
            "version": version,
            "signature": api_sign_request(
                {"public_id": public_id, "version": version},
                "test-secret",
                signature_version=1,
            ),
            # These are deliberately untrusted; the view must use Admin API data.
            "resource_type": "raw",
            "format": "pdf",
            "bytes": 999999999,
        }

    def _arm_upload_nonce(self, public_id):
        session = self.client.session
        session["pending_job_photo_uploads"] = {
            "test-nonce": {
                "public_ids": [public_id],
                "expires_at": 2_000_000_000,
            }
        }
        session.save()

    def test_signing_requires_csrf_and_employee_job_assignment(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(self.url, {"upload_action": "sign", "count": "1"})
        self.assertEqual(response.status_code, 403)

        unassigned = Booking.objects.create(
            customer=self.customer,
            service_type="House Cleaning",
            booking_date=date(2026, 10, 21),
            booking_time=time(10, 0),
            address="1 Test Street",
            suburb_postcode="Adelaide 5000",
        )
        response = self.client.post(
            reverse("upload_job_photo", args=[unassigned.pk]),
            {"upload_action": "sign", "count": "1"},
        )
        self.assertEqual(response.status_code, 404)

    @patch("employees.views.cloudinary_api.resources_by_ids")
    def test_valid_signature_uses_canonical_cloudinary_metadata(self, resources_by_ids):
        public_id = f"job_photos/{self.booking.pk}/photo-1"
        resources_by_ids.return_value = {
            "resources": [
                {
                    "public_id": public_id,
                    "version": 123,
                    "resource_type": "image",
                    "format": "jpg",
                    "bytes": 2048,
                }
            ]
        }
        self._arm_upload_nonce(public_id)
        response = self.client.post(
            self.url,
            {
                "photo_type": "before",
                "cloudinary_nonce": "test-nonce",
                "cloudinary_uploads": json.dumps([self._signed_receipt(public_id)]),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobPhoto.objects.filter(booking=self.booking).count(), 1)
        resources_by_ids.assert_called_once()

    @patch("employees.views._destroy_job_photo_assets")
    @patch("employees.views.cloudinary_api.resources_by_ids")
    def test_oversize_cloudinary_asset_is_deleted_without_saving_photo(
        self, resources_by_ids, destroy_assets
    ):
        public_id = f"job_photos/{self.booking.pk}/too-large"
        resources_by_ids.return_value = {
            "resources": [
                {
                    "public_id": public_id,
                    "version": 123,
                    "resource_type": "image",
                    "format": "jpg",
                    "bytes": 25 * 1024 * 1024 + 1,
                }
            ]
        }
        self._arm_upload_nonce(public_id)
        response = self.client.post(
            self.url,
            {
                "photo_type": "before",
                "cloudinary_nonce": "test-nonce",
                "cloudinary_uploads": json.dumps([self._signed_receipt(public_id)]),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobPhoto.objects.filter(booking=self.booking).count(), 0)
        destroy_assets.assert_called_once_with([public_id])

    @patch("employees.views._destroy_job_photo_assets")
    @patch("employees.views.JobPhoto.save", side_effect=RuntimeError("database failure"))
    @patch("employees.views.cloudinary_api.resources_by_ids")
    def test_database_failure_cleans_cloudinary_asset_and_saves_no_photo(
        self, resources_by_ids, _save, destroy_assets
    ):
        public_id = f"job_photos/{self.booking.pk}/db-failure"
        resources_by_ids.return_value = {
            "resources": [
                {
                    "public_id": public_id,
                    "version": 123,
                    "resource_type": "image",
                    "format": "png",
                    "bytes": 2048,
                }
            ]
        }
        self._arm_upload_nonce(public_id)
        response = self.client.post(
            self.url,
            {
                "photo_type": "after",
                "cloudinary_nonce": "test-nonce",
                "cloudinary_uploads": json.dumps([self._signed_receipt(public_id)]),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobPhoto.objects.filter(booking=self.booking).count(), 0)
        destroy_assets.assert_called_once_with([public_id])

