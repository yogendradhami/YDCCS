from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from bookings.models import Booking, BookingWorkOrder
from core.test_utils import grant_dashboard_permissions
from customers.models import Customer
from .models import Invoice
from .services import get_or_create_invoice_for_booking


class ManualInvoiceEmailTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            full_name="Invoice Recipient",
            email="recipient@example.com",
            phone="0400000000",
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="250.00",
        )
        self.user = get_user_model().objects.create_user(
            username="manual-invoice-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(
            self.user,
            "invoices.add_invoice",
            "invoices.view_invoice",
        )
        self.client.force_login(self.user)
        self.form_data = {
            "booking": self.booking.pk,
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
            "description": "Office cleaning",
            "amount": "250.00",
            "status": "draft",
            "notes": "",
        }

    @patch("dashboard.views.send_invoice_email", return_value=True)
    def test_manual_invoice_is_emailed_after_creation(self, send_invoice_email):
        response = self.client.post(reverse("create_invoice"), self.form_data)

        self.assertEqual(response.status_code, 302, response.content[:500])
        invoice = Invoice.objects.get()
        self.assertRedirects(
            response,
            reverse("invoice_detail", args=[invoice.pk]),
            fetch_redirect_response=False,
        )
        send_invoice_email.assert_called_once_with(response.wsgi_request, invoice)
        self.assertEqual(invoice.booking_id, self.booking.pk)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("created and emailed" in message.message for message in messages)
        )

    def test_create_invoice_page_renders_work_order_formset(self):
        response = self.client.get(reverse("create_invoice"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Work orders")
        self.assertContains(response, 'id="id_work_orders-TOTAL_FORMS"')

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_invoice_email_sends_customer_pdf(self):
        invoice = Invoice.objects.create(
            booking=self.booking,
            description="Office cleaning",
            amount=Decimal("250.00"),
        )
        request = RequestFactory().get("/")
        request.user = self.user

        from dashboard.views import send_invoice_email

        self.assertTrue(send_invoice_email(request, invoice))
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["recipient@example.com"])
        self.assertEqual(sent_email.attachments[0][0], f"{invoice.invoice_number}.pdf")
        self.assertEqual(sent_email.attachments[0][2], "application/pdf")

    @patch("dashboard.views.send_invoice_email", return_value=True)
    def test_manual_invoice_creation_does_not_duplicate_a_booking_invoice(
        self, send_invoice_email
    ):
        first_response = self.client.post(reverse("create_invoice"), self.form_data)
        invoice = Invoice.objects.get()

        second_response = self.client.post(reverse("create_invoice"), self.form_data)

        self.assertRedirects(
            first_response,
            reverse("invoice_detail", args=[invoice.pk]),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            second_response,
            reverse("invoice_detail", args=[invoice.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(Invoice.objects.count(), 1)
        send_invoice_email.assert_called_once()

    @patch("dashboard.views.send_invoice_email", return_value=True)
    def test_manual_invoice_sums_multiple_work_orders(
        self, send_invoice_email
    ):
        data = {
            **self.form_data,
            "amount": "175.00",
            "work_orders-TOTAL_FORMS": "2",
            "work_orders-INITIAL_FORMS": "0",
            "work_orders-MIN_NUM_FORMS": "1",
            "work_orders-MAX_NUM_FORMS": "1000",
            "work_orders-0-description": "Office Cleaning",
            "work_orders-0-price": "100.00",
            "work_orders-1-description": "Carpet Cleaning",
            "work_orders-1-price": "75.00",
        }

        response = self.client.post(reverse("create_invoice"), data)

        self.assertEqual(response.status_code, 302, response.content[:500])
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.amount, Decimal("175.00"))
        self.assertEqual(invoice.gst_amount, Decimal("17.500"))
        self.assertEqual(invoice.total_amount, Decimal("192.500"))
        self.assertEqual(
            list(invoice.work_orders.values_list("description", "price", "position")),
            [
                ("Office Cleaning", Decimal("100.00"), 0),
                ("Carpet Cleaning", Decimal("75.00"), 1),
            ],
        )
        detail_response = self.client.get(
            reverse("invoice_detail", args=[invoice.pk])
        )
        self.assertContains(detail_response, "1. Office Cleaning")
        self.assertContains(detail_response, "2. Carpet Cleaning")
        send_invoice_email.assert_called_once()

    @patch("dashboard.views.send_invoice_email", return_value=False)
    def test_failed_email_reports_invoice_was_created(self, send_invoice_email):
        response = self.client.post(reverse("create_invoice"), self.form_data)

        self.assertEqual(response.status_code, 302, response.content[:500])
        self.assertEqual(Invoice.objects.count(), 1)
        send_invoice_email.assert_called_once()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("could not be sent" in message.message for message in messages)
        )


class InvoiceBookingServiceTests(TestCase):
    def test_invoice_detail_formats_currency_to_two_decimal_places(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="100.00",
        )
        invoice = Invoice.objects.create(booking=booking, amount=Decimal("100.00"))
        user = get_user_model().objects.create_user(
            username="invoice-detail-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(user, "invoices.view_invoice")
        self.client.force_login(user)

        response = self.client.get(
            reverse("invoice_detail", args=[invoice.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "$110.00")
        self.assertNotContains(response, "$110.0000")

    def test_invoice_creation_is_idempotent_for_a_booking(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="250.00",
        )

        first, created = get_or_create_invoice_for_booking(booking)
        second, second_created = get_or_create_invoice_for_booking(booking)

        self.assertTrue(created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.booking_id, booking.pk)
        self.assertEqual(first.invoice_number, "YD-00001")
        self.assertEqual(first.amount, Decimal("250.00"))
        self.assertEqual(first.status, "draft")
        self.assertEqual(Invoice.objects.count(), 1)

    def test_invoice_creation_copies_all_booking_work_orders(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="175.00",
        )
        BookingWorkOrder.objects.create(
            booking=booking,
            service_type="Office Cleaning",
            price=Decimal("100.00"),
            position=0,
        )
        BookingWorkOrder.objects.create(
            booking=booking,
            service_type="Carpet Cleaning",
            price=Decimal("75.00"),
            position=1,
        )

        invoice, created = get_or_create_invoice_for_booking(booking)

        self.assertTrue(created)
        self.assertEqual(invoice.amount, Decimal("175.00"))
        self.assertEqual(invoice.total_amount, Decimal("192.500"))
        self.assertEqual(invoice.work_orders.count(), 2)
        self.assertEqual(invoice.work_orders.first().description, "Office Cleaning")
        self.assertEqual(invoice.work_orders.last().description, "Carpet Cleaning")

    def test_deleting_invoice_preserves_booking_customer_and_other_invoices(self):
        customer = Customer.objects.create(
            full_name="Invoice History Customer",
            email="invoice-history@example.com",
            phone="0400000000",
        )
        booking = Booking.objects.create(
            customer=customer,
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="250.00",
        )
        invoice = Invoice.objects.create(booking=booking)
        additional_invoice = Invoice.objects.create(booking=booking)
        admin = get_user_model().objects.create_user(
            username="invoice-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(admin, "invoices.delete_invoice")
        self.client.force_login(admin)

        response = self.client.post(reverse("delete_invoice", args=[invoice.pk]))

        self.assertRedirects(
            response,
            reverse("invoice_list"),
            fetch_redirect_response=False,
        )
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())
        self.assertTrue(Invoice.objects.filter(pk=additional_invoice.pk).exists())
        self.assertTrue(Booking.objects.filter(pk=booking.pk).exists())
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())

    def test_invoice_list_renders_kpis_from_stats_context(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="100.00",
        )
        Invoice.objects.create(booking=booking, amount=Decimal("100.00"), status="paid")
        Invoice.objects.create(booking=booking, amount=Decimal("100.00"), status="sent")
        admin = get_user_model().objects.create_user(
            username="invoice-list-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(admin, "invoices.view_invoice")
        self.client.force_login(admin)

        response = self.client.get(reverse("invoice_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["invoices"].count(), 2)
        self.assertEqual(response.context["stats"]["total_invoiced"], Decimal("220.000"))
        self.assertEqual(response.context["stats"]["paid_total"], Decimal("110.000"))
        self.assertEqual(response.context["stats"]["outstanding_total"], Decimal("110.000"))
        self.assertEqual(response.context["stats"]["invoice_count"], 2)
        self.assertEqual(response.context["stats"]["paid_count"], 1)
        self.assertContains(response, "$220.00")
        self.assertContains(response, "$110.00")

    def test_invoice_list_groups_separate_booking_invoices_by_customer(self):
        customer = Customer.objects.create(
            full_name="Grouped Invoice Customer",
            email="grouped@example.com",
            phone="0400000000",
        )
        invoices = []
        for booking_date in (
            date.today() + timedelta(days=1),
            date.today() + timedelta(days=2),
        ):
            booking = Booking.objects.create(
                customer=customer,
                service_type="Office Cleaning",
                booking_date=booking_date,
                booking_time=time(10, 0),
                address="1 King Street",
                suburb_postcode="Adelaide 5000",
                quoted_price="100.00",
            )
            invoices.append(Invoice.objects.create(booking=booking))

        admin = get_user_model().objects.create_user(
            username="grouped-invoice-list-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(admin, "invoices.view_invoice")
        self.client.force_login(admin)

        response = self.client.get(reverse("invoice_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["invoices"].count(), 2)
        self.assertContains(response, 'class="invoice-customer-group"')
        self.assertContains(response, "Grouped Invoice Customer", count=1)
        self.assertContains(response, invoices[0].invoice_number)
        self.assertContains(response, invoices[1].invoice_number)

    def test_customer_profile_revenue_sums_only_paid_customer_invoices(self):
        customer = Customer.objects.create(
            full_name="Revenue Customer",
            email="revenue@example.com",
            phone="0400000000",
            total_revenue=Decimal("999.00"),
        )
        for booking_date, amount, status in (
            (date.today() + timedelta(days=1), "100.00", "paid"),
            (date.today() + timedelta(days=2), "200.00", "sent"),
        ):
            booking = Booking.objects.create(
                customer=customer,
                service_type="Office Cleaning",
                booking_date=booking_date,
                booking_time=time(10, 0),
                address="1 King Street",
                suburb_postcode="Adelaide 5000",
                quoted_price=amount,
            )
            Invoice.objects.create(
                booking=booking,
                amount=Decimal(amount),
                status=status,
            )

        admin = get_user_model().objects.create_user(
            username="customer-revenue-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(
            admin,
            "customers.view_customer",
            "bookings.view_booking",
            "invoices.view_invoice",
            "reviews.view_review",
            "dashboard.view_emaillog",
            "quotes.view_quoterequest",
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("customer_profile_360", args=[customer.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_spent"], Decimal("110.000"))
        self.assertContains(response, "110.00")

        legacy_response = self.client.get(reverse("customer_360", args=[customer.pk]))

        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(
            legacy_response.context["total_revenue"],
            Decimal("110.000"),
        )
        self.assertContains(legacy_response, "$110.00")
