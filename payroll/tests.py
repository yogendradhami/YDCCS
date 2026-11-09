from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from employees.models import Employee
from induction.models import EmployeeInduction, InductionProgramme

from .forms import PayrollRecordForm
from .models import PayrollRecord
from .views import send_payroll_email


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PayrollEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payroll-employee",
            email="employee@example.com",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Payroll Employee",
            phone="0400000000",
            hourly_rate=Decimal("35.00"),
        )
        self.payroll = PayrollRecord.objects.create(
            employee=self.employee,
            period_start=date(2026, 11, 3),
            period_end=date(2026, 11, 9),
            total_hours=Decimal("12.50"),
            hourly_rate=Decimal("35.00"),
            gross_pay=Decimal("437.50"),
            status="draft",
        )

    def test_payroll_notification_is_branded_and_attaches_pdf(self):
        sent = send_payroll_email(self.payroll, "generated")

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["employee@example.com"])
        self.assertIn("Your payroll statement is ready", email.subject)
        self.assertEqual(len(email.alternatives), 1)
        html_body, content_type = email.alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("YD Commercial Cleaning", html_body)
        self.assertIn("PAY-000001", html_body)
        self.assertIn("$437.50 AUD", html_body)
        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.status, "sent")
        self.assertEqual(
            self.payroll.payment_status,
            PayrollRecord.PaymentStatus.IN_PROCESS,
        )
        self.assertEqual(len(email.attachments), 1)
        filename, content, mime_type = email.attachments[0]
        self.assertTrue(filename.endswith(".pdf"))
        self.assertEqual(mime_type, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF-"))

    def test_employee_account_email_is_used_when_profile_email_is_empty(self):
        self.employee.email = ""
        self.employee.save(update_fields=["email"])

        sent = send_payroll_email(self.payroll, "approved")

        self.assertTrue(sent)
        self.assertEqual(mail.outbox[0].to, ["employee@example.com"])
        self.assertIn("approved", mail.outbox[0].subject.lower())

    def test_paid_notification_uses_the_same_branded_template_and_pdf(self):
        self.payroll.status = "paid"
        self.payroll.save(update_fields=["status"])

        sent = send_payroll_email(self.payroll, "paid")

        self.assertTrue(sent)
        email = mail.outbox[0]
        self.assertIn("Your payroll has been paid", email.alternatives[0][0])
        self.assertEqual(len(email.attachments), 1)
        self.assertEqual(email.attachments[0][2], "application/pdf")

    @patch("payroll.views.EmailMultiAlternatives.send", return_value=0)
    def test_failed_email_keeps_record_as_draft(self, _send):
        self.assertFalse(send_payroll_email(self.payroll, "generated"))

        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.status, "draft")
        self.assertEqual(
            self.payroll.payment_status,
            PayrollRecord.PaymentStatus.NOT_STARTED,
        )

    def test_payroll_form_rejects_reversed_period_and_negative_hours(self):
        form = PayrollRecordForm(
            data={
                "employee": self.employee.pk,
                "period_start": "2026-11-10",
                "period_end": "2026-11-09",
                "total_hours": "-1",
                "hourly_rate": "35.00",
                "gross_pay": "437.50",
                "notes": "",
            },
            instance=self.payroll,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("period_end", form.errors)
        self.assertIn("total_hours", form.errors)


class PayrollRecordManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="payroll-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.employee = Employee.objects.create(
            user=User.objects.create_user(username="payroll-owner"),
            full_name="Payroll Employee",
            phone="0400000000",
        )
        self.payroll = PayrollRecord.objects.create(
            employee=self.employee,
            period_start=date(2026, 11, 3),
            period_end=date(2026, 11, 9),
            total_hours=Decimal("12.50"),
            hourly_rate=Decimal("35.00"),
            gross_pay=Decimal("437.50"),
            status="sent",
            payment_status=PayrollRecord.PaymentStatus.IN_PROCESS,
        )
        self.client.force_login(self.admin)

    def test_payroll_detail_and_update_views(self):
        response = self.client.get(
            reverse("payroll_detail", args=[self.payroll.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In process")

        response = self.client.post(
            reverse("edit_payroll", args=[self.payroll.pk]),
            {
                "employee": self.employee.pk,
                "period_start": "2026-11-03",
                "period_end": "2026-11-09",
                "total_hours": "14.00",
                "hourly_rate": "35.00",
                "gross_pay": "490.00",
                "notes": "Corrected attendance hours",
            },
        )
        self.assertRedirects(
            response,
            reverse("payroll_detail", args=[self.payroll.pk]),
        )
        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.total_hours, Decimal("14.00"))
        self.assertEqual(self.payroll.gross_pay, Decimal("490.00"))
        self.assertEqual(self.payroll.status, "sent")
        self.assertEqual(
            self.payroll.payment_status,
            PayrollRecord.PaymentStatus.IN_PROCESS,
        )

    def test_payroll_delete_requires_post_confirmation(self):
        response = self.client.get(
            reverse("delete_payroll", args=[self.payroll.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PayrollRecord.objects.filter(pk=self.payroll.pk).exists())

        response = self.client.post(
            reverse("delete_payroll", args=[self.payroll.pk])
        )
        self.assertRedirects(response, reverse("payroll_list"))
        self.assertFalse(PayrollRecord.objects.filter(pk=self.payroll.pk).exists())

    def test_payroll_register_groups_periods_under_one_employee_name(self):
        PayrollRecord.objects.create(
            employee=self.employee,
            period_start=date(2026, 10, 27),
            period_end=date(2026, 11, 2),
            total_hours=Decimal("10.00"),
            hourly_rate=Decimal("35.00"),
            gross_pay=Decimal("350.00"),
            status="paid",
            payment_status=PayrollRecord.PaymentStatus.PAID,
        )

        response = self.client.get(reverse("payroll_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["payroll_groups"]), 1)
        self.assertEqual(
            len(response.context["payroll_groups"][0]["records"]),
            2,
        )
        self.assertEqual(
            response.content.decode().count(
                '<details class="payroll-employee-group" data-payroll-group'
            ),
            1,
        )
        self.assertEqual(
            response.content.decode().count("<strong>Payroll Employee</strong>"),
            1,
        )

    def test_payslip_download_is_limited_to_owner_or_payroll_managers(self):
        response = self.client.get(
            reverse("download_payslip_pdf", args=[self.payroll.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

        other_user = User.objects.create_user(username="other-payroll-user")
        other_employee = Employee.objects.create(
            user=other_user,
            full_name="Other Employee",
            phone="0400000001",
        )
        programme = InductionProgramme.objects.create()
        EmployeeInduction.objects.create(
            employee=self.employee,
            programme=programme,
            status="completed",
        )
        EmployeeInduction.objects.create(
            employee=other_employee,
            programme=programme,
            status="completed",
        )
        self.client.force_login(other_user)
        response = self.client.get(
            reverse("employee_download_payslip_pdf", args=[self.payroll.pk])
        )
        self.assertEqual(response.status_code, 403, response.get("Location"))

        self.client.force_login(self.employee.user)
        response = self.client.get(
            reverse("employee_download_payslip_pdf", args=[self.payroll.pk])
        )
        self.assertEqual(response.status_code, 200)
