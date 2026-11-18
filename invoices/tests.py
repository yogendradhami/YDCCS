from datetime import date, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
import fitz

from django.db import connection
from bookings.models import Booking, BookingWorkOrder
from core.test_utils import grant_dashboard_permissions
from customers.models import Customer
from .models import Invoice, StripeWebhookEvent
from .payment_links import (
    STRIPE_PAYMENT_LINK_SALT,
    get_invoice_id_from_payment_token,
    get_invoice_payment_token,
    get_invoice_payment_url,
)
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
            "invoices.change_invoice",
            "invoices.view_invoice",
            "customers.view_customer",
            "bookings.view_booking",
            "reviews.view_review",
            "dashboard.view_emaillog",
            "quotes.view_quoterequest",
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
    def test_manual_invoice_email_is_opt_in_and_off_by_default(self, send_invoice_email):
        response = self.client.post(reverse("create_invoice"), self.form_data)

        self.assertEqual(response.status_code, 302, response.content[:500])
        invoice = Invoice.objects.get()
        self.assertRedirects(
            response,
            reverse("invoice_detail", args=[invoice.pk]),
            fetch_redirect_response=False,
        )
        send_invoice_email.assert_not_called()
        self.assertNotEqual(invoice.booking_id, self.booking.pk)
        self.assertEqual(invoice.booking.customer_id, self.customer.pk)
        self.assertEqual(invoice.booking.service_type, self.booking.service_type)
        self.assertEqual(invoice.booking.booking_date, self.booking.booking_date)
        self.assertEqual(invoice.booking.booking_time, self.booking.booking_time)
        self.assertEqual(invoice.booking.address, self.booking.address)
        self.assertEqual(
            invoice.booking.assigned_employee_id,
            self.booking.assigned_employee_id,
        )
        self.assertEqual(invoice.booking.status, "pending")
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any(
                "No email was sent" in message.message
                for message in messages
            )
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_creating_paid_invoice_completes_booking_and_updates_customer_without_email(
        self,
    ):
        response = self.client.post(
            reverse("create_invoice"),
            {**self.form_data, "status": "paid"},
        )

        self.assertEqual(response.status_code, 302, response.content[:500])
        invoice = Invoice.objects.get()
        created_booking = invoice.booking
        self.booking.refresh_from_db()
        self.customer.refresh_from_db()

        self.assertEqual(invoice.status, "paid")
        self.assertIsNotNone(invoice.paid_at)
        self.assertNotEqual(created_booking.pk, self.booking.pk)
        self.assertEqual(created_booking.status, "completed")
        self.assertEqual(created_booking.quoted_price, Decimal("250.00"))
        self.assertEqual(self.booking.status, "pending")
        self.assertEqual(self.customer.jobs_completed, 1)
        self.assertEqual(self.customer.total_revenue, Decimal("275.000"))
        self.assertEqual(mail.outbox, [])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_marking_invoice_paid_completes_booking_without_email(self):
        invoice = Invoice.objects.create(
            booking=self.booking,
            amount=Decimal("250.00"),
        )

        response = self.client.post(
            reverse("mark_invoice_paid", args=[invoice.pk]),
        )

        self.assertRedirects(
            response,
            reverse("invoice_list"),
            fetch_redirect_response=False,
        )
        invoice.refresh_from_db()
        self.booking.refresh_from_db()
        self.customer.refresh_from_db()

        self.assertEqual(invoice.status, "paid")
        self.assertIsNotNone(invoice.paid_at)
        self.assertEqual(self.booking.status, "completed")
        self.assertEqual(self.booking.quoted_price, Decimal("250.00"))
        self.assertEqual(self.customer.jobs_completed, 1)
        self.assertEqual(self.customer.total_revenue, Decimal("275.000"))
        self.assertEqual(mail.outbox, [])
        self.assertTrue(
            any(
                "No email was sent" in message.message
                for message in response.wsgi_request._messages
            )
        )

    def test_marking_already_paid_invoice_repairs_booking_completion(self):
        invoice = Invoice.objects.create(
            booking=self.booking,
            amount=Decimal("250.00"),
        )
        Invoice.objects.filter(pk=invoice.pk).update(status="paid")

        response = self.client.post(
            reverse("mark_invoice_paid", args=[invoice.pk]),
        )

        self.assertRedirects(
            response,
            reverse("invoice_list"),
            fetch_redirect_response=False,
        )
        self.booking.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(self.booking.status, "completed")
        self.assertEqual(self.booking.quoted_price, Decimal("250.00"))
        self.assertEqual(self.customer.jobs_completed, 1)
        self.assertEqual(self.customer.total_revenue, Decimal("275.000"))

    def test_editing_invoice_status_returns_to_invoice_list(self):
        invoice = Invoice.objects.create(
            booking=self.booking,
            amount=Decimal("250.00"),
        )

        response = self.client.post(
            reverse("edit_invoice", args=[invoice.pk]),
            {**self.form_data, "status": "sent"},
        )

        self.assertRedirects(
            response,
            reverse("invoice_list"),
            fetch_redirect_response=False,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "sent")

    def test_paid_invoices_sync_all_customer_bookings_and_profile_totals(self):
        second_booking = Booking.objects.create(
            customer=self.customer,
            service_type="Window Cleaning",
            booking_date=date.today() + timedelta(days=2),
            booking_time=time(11, 0),
            address="2 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="300.00",
        )
        invoices = [
            Invoice.objects.create(booking=booking, amount=amount)
            for booking, amount in (
                (self.booking, Decimal("250.00")),
                (second_booking, Decimal("300.00")),
            )
        ]
        Invoice.objects.filter(pk__in=[invoice.pk for invoice in invoices]).update(
            status="paid"
        )

        response = self.client.post(
            reverse("mark_invoice_paid", args=[invoices[0].pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        second_booking.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(self.booking.status, "completed")
        self.assertEqual(second_booking.status, "completed")
        self.assertEqual(self.customer.jobs_completed, 2)
        self.assertEqual(self.customer.total_revenue, Decimal("605.000"))

        profile_response = self.client.get(
            reverse("customer_profile_360", args=[self.customer.pk]),
        )
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.context["total_bookings"], 2)
        self.assertEqual(profile_response.context["completed_bookings"], 2)

    def test_create_invoice_page_renders_work_order_formset(self):
        response = self.client.get(reverse("create_invoice"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Work orders")
        self.assertContains(response, 'id="id_work_orders-TOTAL_FORMS"')
        self.assertContains(
            response,
            'name="send_invoice_email"',
        )
        self.assertContains(
            response,
            "Email this invoice to the customer after creation",
        )

    @patch("dashboard.views.send_invoice_email", return_value=True)
    def test_manual_invoice_can_be_emailed_when_explicitly_selected(
        self, send_invoice_email
    ):
        response = self.client.post(
            reverse("create_invoice"),
            {**self.form_data, "send_invoice_email": "on"},
        )

        self.assertEqual(response.status_code, 302)
        invoice = Invoice.objects.get()
        send_invoice_email.assert_called_once_with(response.wsgi_request, invoice)
        self.assertTrue(
            any(
                f"Invoice {invoice.invoice_number} created and emailed"
                in message.message
                for message in response.wsgi_request._messages
            )
        )

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
        self.assertTrue(sent_email.attachments[0][1].startswith(b"%PDF-"))
        self.assertGreater(len(sent_email.attachments[0][1]), 1000)
        self.assertIn("/invoice/pay/", sent_email.body)
        self.assertIn("/invoice/pay/", sent_email.alternatives[0][0])
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "sent")
        self.assertContains(
            self.client.get(reverse("invoice_detail", args=[invoice.pk])),
            "Sent",
        )
        self.assertContains(
            self.client.get(reverse("invoice_list")),
            "Sent",
        )

    def test_dashboard_invoice_download_returns_a_complete_pdf(self):
        invoice = Invoice.objects.create(
            booking=self.booking,
            description="Office cleaning",
            amount=Decimal("250.00"),
        )

        response = self.client.get(
            reverse("download_invoice_pdf", args=[invoice.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(
            f'filename="{invoice.invoice_number}.pdf"',
            response["Content-Disposition"],
        )
        pdf_content = b"".join(response.streaming_content)
        self.assertTrue(pdf_content.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_content), 1000)
        pdf_text = " ".join(
            page.get_text()
            for page in fitz.open(stream=pdf_content, filetype="pdf")
        ).split()
        pdf_text = " ".join(pdf_text)
        for expected_text in (
            "TERMS & CONDITIONS",
            "Payment is due within 7 days from the invoice date",
            "All payments must include the relevant invoice number",
            "Any additional services or variations outside the agreed scope",
            "A minimum of 24 hours' written notice",
            "Any concerns regarding service quality must be reported within 24 hours",
            "recovery of overdue accounts in accordance with applicable laws",
            "Thank you for your business. We appreciate your trust in",
            "BANK DETAILS",
            "YD Commercial Cleaning Services",
            "035-050",
            "407482",
            "PAY ONLINE",
            "PAY NOW",
            invoice.invoice_number,
        ):
            self.assertIn(expected_text, pdf_text)
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        self.assertTrue(
            any(
                link.get("uri", "").startswith(
                    "https://www.ydcleaning.com.au/invoice/pay/"
                )
                for page in pdf_document
                for link in page.get_links()
            )
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_successful_invoice_email_keeps_sent_status_after_due_date(self):
        invoice = Invoice.objects.create(
            booking=self.booking,
            description="Office cleaning",
            amount=Decimal("250.00"),
            issue_date=date.today() - timedelta(days=30),
            due_date=date.today() - timedelta(days=16),
        )
        request = RequestFactory().get("/")
        request.user = self.user

        from dashboard.views import send_invoice_email

        self.assertTrue(send_invoice_email(request, invoice))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "sent")


@override_settings(
    STRIPE_SECRET_KEY="sk_test_value",
    STRIPE_WEBHOOK_SECRET="whsec_test_value",
    STRIPE_CURRENCY="aud",
    SITE_URL="https://www.ydcleaning.com.au",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="billing@example.com",
)
class StripeInvoicePaymentTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            full_name="Stripe Recipient",
            email="stripe-recipient@example.com",
            phone="0400000000",
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="100.00",
        )
        self.invoice = Invoice.objects.create(
            booking=self.booking,
            description="Office cleaning",
            amount=Decimal("100.00"),
            status="sent",
        )
        self.session_id = "cs_test_invoice"
        self.invoice.stripe_checkout_session_id = self.session_id
        self.invoice.status = "pending"
        self.invoice.save(
            update_fields=["stripe_checkout_session_id", "status"]
        )

    def _paid_session(self, **overrides):
        session = {
            "id": self.session_id,
            "metadata": {
                "invoice_id": str(self.invoice.pk),
                "invoice_number": self.invoice.invoice_number,
            },
            "client_reference_id": str(self.invoice.pk),
            "mode": "payment",
            "currency": "aud",
            "amount_total": int(self.invoice.total_amount * 100),
            "payment_status": "paid",
            "payment_intent": "pi_test_invoice",
            "payment_method_types": ["card"],
        }
        session.update(overrides)
        return session

    def _post_webhook(self, event_id, session=None, event_type="checkout.session.completed"):
        event = {
            "id": event_id,
            "type": event_type,
            "created": 1_750_000_000,
            "data": {"object": session or self._paid_session()},
        }
        with patch("invoices.views.verify_webhook", return_value=event):
            return self.client.post(
                reverse("stripe_webhook"),
                data=b"verified-by-mock",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="signature",
            )

    @patch("invoices.stripe_service.stripe.checkout.Session.create")
    def test_signed_payment_link_creates_aud_checkout_for_invoice_total(
        self, create_session
    ):
        create_session.return_value = SimpleNamespace(
            id="cs_test_new",
            url="https://checkout.stripe.com/c/pay/cs_test_new",
        )
        invoice = self.invoice
        invoice.status = "sent"
        invoice.stripe_checkout_session_id = ""
        invoice.stripe_checkout_idempotency_key = ""
        invoice.save(
            update_fields=[
                "status",
                "stripe_checkout_session_id",
                "stripe_checkout_idempotency_key",
            ]
        )

        response = self.client.get(
            get_invoice_payment_url(invoice).replace(
                "https://www.ydcleaning.com.au", ""
            )
        )

        self.assertRedirects(
            response,
            "https://checkout.stripe.com/c/pay/cs_test_new",
            fetch_redirect_response=False,
        )
        parameters = create_session.call_args.kwargs
        self.assertEqual(parameters["mode"], "payment")
        self.assertEqual(
            parameters["line_items"][0]["price_data"]["currency"],
            "aud",
        )
        self.assertEqual(
            parameters["line_items"][0]["price_data"]["unit_amount"],
            int(invoice.total_amount * 100),
        )
        self.assertEqual(parameters["metadata"]["invoice_id"], str(invoice.pk))
        self.assertEqual(
            parameters["metadata"]["invoice_number"],
            invoice.invoice_number,
        )
        self.assertNotIn("timeout", parameters)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "pending")
        self.assertEqual(invoice.stripe_checkout_session_id, "cs_test_new")
        self.assertTrue(invoice.stripe_checkout_idempotency_key)

    @patch("invoices.stripe_service.stripe.checkout.Session.create")
    @patch("invoices.stripe_service.stripe.checkout.Session.retrieve")
    def test_open_checkout_session_is_reused(
        self, retrieve_session, create_session
    ):
        retrieve_session.return_value = SimpleNamespace(
            status="open",
            url="https://checkout.stripe.com/c/pay/cs_test_invoice",
        )
        response = self.client.get(
            get_invoice_payment_url(self.invoice).replace(
                "https://www.ydcleaning.com.au", ""
            )
        )

        self.assertEqual(response.status_code, 302)
        retrieve_session.assert_called_once_with(self.session_id)
        create_session.assert_not_called()

    @skipUnless(
        connection.vendor == "postgresql",
        "PostgreSQL locking regression requires a PostgreSQL test database.",
    )
    @patch("invoices.stripe_service.stripe.checkout.Session.create")
    def test_postgres_checkout_locks_only_invoice_with_nullable_customer(
        self, create_session
    ):
        create_session.return_value = SimpleNamespace(
            id="cs_test_postgres",
            url="https://checkout.stripe.com/c/pay/cs_test_postgres",
        )
        self.invoice.stripe_checkout_session_id = ""
        self.invoice.stripe_checkout_idempotency_key = ""
        self.invoice.status = "sent"
        self.invoice.save(
            update_fields=[
                "stripe_checkout_session_id",
                "stripe_checkout_idempotency_key",
                "status",
            ]
        )
        self.booking.customer = None
        self.booking.save(update_fields=["customer"])
        self.invoice.refresh_from_db()

        from .stripe_service import create_checkout_session

        session = create_checkout_session(
            self.invoice,
            "https://example.com/success",
            "https://example.com/cancel",
        )

        self.assertEqual(session.id, "cs_test_postgres")
        self.assertTrue(create_session.called)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")
        self.assertEqual(
            self.invoice.stripe_checkout_session_id,
            "cs_test_postgres",
        )

    def test_invalid_webhook_signature_is_rejected(self):
        with patch(
            "invoices.views.verify_webhook",
            side_effect=ValueError("Invalid signature"),
        ):
            response = self.client.post(
                reverse("stripe_webhook"),
                data=b"untrusted",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="invalid",
            )

        self.assertEqual(response.status_code, 400)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")

    def test_paid_webhook_updates_invoice_and_sends_pdf_confirmation_once(self):
        response = self._post_webhook("evt_paid")
        self.assertEqual(response.status_code, 200)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "paid")
        self.assertEqual(self.invoice.stripe_payment_intent_id, "pi_test_invoice")
        self.assertEqual(self.invoice.payment_method, "Stripe (card)")
        self.assertTrue(self.invoice.payment_confirmation_email_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].attachments[0][0],
            f"{self.invoice.invoice_number}.pdf",
        )
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)

        duplicate_response = self._post_webhook("evt_paid")
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_unpaid_checkout_event_does_not_mark_invoice_paid(self):
        response = self._post_webhook(
            "evt_unpaid",
            session=self._paid_session(payment_status="unpaid"),
        )

        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")
        self.assertFalse(self.invoice.payment_confirmation_email_sent)

    def test_failed_async_payment_event_does_not_mark_invoice_paid(self):
        response = self._post_webhook(
            "evt_failed",
            event_type="checkout.session.async_payment_failed",
        )

        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "sent")
        self.assertEqual(self.invoice.stripe_checkout_session_id, "")

    def test_payment_return_page_does_not_mark_invoice_paid(self):
        token = get_invoice_payment_token(self.invoice)
        response = self.client.get(
            reverse("stripe_payment_return", kwargs={"token": token})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "being verified")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")

    def test_invalid_session_amount_is_not_accepted(self):
        response = self._post_webhook(
            "evt_wrong_amount",
            session=self._paid_session(amount_total=1),
        )

        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")

    def test_paid_and_cancelled_invoices_cannot_start_checkout(self):
        token = get_invoice_payment_token(self.invoice)
        self.invoice.status = "cancelled"
        self.invoice.save(update_fields=["status"])

        with patch("invoices.stripe_service.stripe.checkout.Session.create") as create:
            response = self.client.get(
                reverse("invoice_stripe_pay_link", kwargs={"token": token})
            )

        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_paid_invoice_cannot_start_checkout(self):
        token = get_invoice_payment_token(self.invoice)
        self.invoice.status = "paid"
        self.invoice.save(update_fields=["status"])

        with patch("invoices.stripe_service.stripe.checkout.Session.create") as create:
            response = self.client.get(
                reverse("invoice_stripe_pay_link", kwargs={"token": token})
            )

        self.assertEqual(response.status_code, 200)
        create.assert_not_called()

    def test_cancel_return_does_not_change_invoice_status(self):
        token = get_invoice_payment_token(self.invoice)
        response = self.client.get(
            reverse("stripe_payment_cancel_return", kwargs={"token": token})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment was cancelled")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "pending")

    def test_signed_link_is_bound_to_an_existing_invoice(self):
        invalid_token = signing.Signer(
            salt=STRIPE_PAYMENT_LINK_SALT
        ).sign(str(self.invoice.pk + 1000))
        with patch("invoices.stripe_service.stripe.checkout.Session.create") as create:
            response = self.client.get(
                reverse("invoice_stripe_pay_link", kwargs={"token": invalid_token})
            )

        self.assertEqual(response.status_code, 404)
        create.assert_not_called()

    def test_existing_timestamped_payment_link_still_starts_checkout(self):
        legacy_token = signing.dumps(
            self.invoice.pk,
            salt=STRIPE_PAYMENT_LINK_SALT,
        )
        self.assertEqual(
            get_invoice_id_from_payment_token(legacy_token),
            str(self.invoice.pk),
        )
        with patch(
            "invoices.stripe_service.stripe.checkout.Session.retrieve",
            return_value=SimpleNamespace(
                status="open",
                url="https://checkout.stripe.com/c/pay/cs_test_invoice",
            ),
        ) as retrieve_session:
            response = self.client.get(
                reverse("invoice_stripe_pay_link", kwargs={"token": legacy_token})
            )

        self.assertRedirects(
            response,
            "https://checkout.stripe.com/c/pay/cs_test_invoice",
            fetch_redirect_response=False,
        )
        retrieve_session.assert_called_once_with("cs_test_invoice")

    def test_payment_link_returns_diagnostic_when_invoice_schema_is_unavailable(self):
        token = get_invoice_payment_token(self.invoice)
        with patch(
            "invoices.views.get_object_or_404",
            side_effect=DatabaseError("missing payment tracking column"),
        ):
            response = self.client.get(
                reverse("invoice_stripe_pay_link", kwargs={"token": token})
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn(
            b"Online invoice payment is temporarily unavailable",
            response.content,
        )

    def test_legacy_token_is_supported_on_success_return(self):
        legacy_token = signing.dumps(
            self.invoice.pk,
            salt=STRIPE_PAYMENT_LINK_SALT,
        )

        response = self.client.get(
            reverse("stripe_payment_return", kwargs={"token": legacy_token})
        )

        self.assertEqual(response.status_code, 200)


class ManualInvoiceEmailContinuationTests(TestCase):
    def setUp(self):
        ManualInvoiceEmailTests.setUp(self)

    @patch("dashboard.views.send_invoice_email", return_value=True)
    def test_manual_invoice_creation_creates_a_separate_booking_for_each_invoice(
        self, send_invoice_email
    ):
        first_response = self.client.post(reverse("create_invoice"), self.form_data)
        first_invoice = Invoice.objects.get()

        second_response = self.client.post(reverse("create_invoice"), self.form_data)
        invoices = list(Invoice.objects.order_by("pk"))
        second_invoice = invoices[-1]

        self.assertRedirects(
            first_response,
            reverse("invoice_detail", args=[first_invoice.pk]),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            second_response,
            reverse("invoice_detail", args=[second_invoice.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(invoices), 2)
        booking_ids = {invoice.booking_id for invoice in invoices}
        self.assertEqual(len(booking_ids), 2)
        self.assertNotIn(self.booking.pk, booking_ids)
        self.assertEqual(Booking.objects.count(), 3)
        self.assertTrue(
            all(invoice.booking.customer_id == self.customer.pk for invoice in invoices)
        )
        self.assertNotEqual(
            first_invoice.invoice_number,
            second_invoice.invoice_number,
        )
        send_invoice_email.assert_not_called()

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
        self.assertEqual(
            list(
                invoice.booking.work_orders.values_list(
                    "service_type", "price", "position"
                )
            ),
            [
                ("Office Cleaning", Decimal("100.00"), 0),
                ("Carpet Cleaning", Decimal("75.00"), 1),
            ],
        )
        self.assertEqual(invoice.booking.quoted_price, Decimal("175.00"))
        detail_response = self.client.get(
            reverse("invoice_detail", args=[invoice.pk])
        )
        self.assertContains(detail_response, "1. Office Cleaning")
        self.assertContains(detail_response, "2. Carpet Cleaning")
        send_invoice_email.assert_not_called()

    @patch("dashboard.views.send_invoice_email", return_value=False)
    def test_manual_invoice_email_failure_does_not_undo_invoice(
        self, send_invoice_email
    ):
        response = self.client.post(
            reverse("create_invoice"),
            {**self.form_data, "send_invoice_email": "on"},
        )

        self.assertEqual(response.status_code, 302, response.content[:500])
        self.assertEqual(Invoice.objects.count(), 1)
        send_invoice_email.assert_called_once()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("customer email could not be sent" in message.message for message in messages)
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
        self.assertIn(b"<!DOCTYPE html>", response.content)
        self.assertContains(response, "YD Commercial Cleaning Services")
        self.assertContains(response, "class=\"invoice-card\"")
        self.assertContains(response, "TERMS &amp; CONDITIONS")
        self.assertContains(response, "BANK DETAILS")
        self.assertContains(response, "035-050")
        self.assertContains(response, "407482")
        self.assertContains(response, "Please use your invoice number.")
        self.assertNotContains(response, "crm-sidebar")
        self.assertNotContains(response, "crm-topbar")
        self.assertNotContains(response, "Pay Now with Stripe")
        self.assertNotContains(response, "Back to Invoices")

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

    def test_invoice_kpis_include_overdue_status_even_when_due_date_is_future(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="100.00",
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=14),
            status="overdue",
        )
        admin = get_user_model().objects.create_user(
            username="overdue-invoice-list-admin",
            is_staff=True,
        )
        grant_dashboard_permissions(admin, "invoices.view_invoice")
        self.client.force_login(admin)

        response = self.client.get(reverse("invoice_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["outstanding_total"], Decimal("110.000"))
        self.assertEqual(response.context["stats"]["outstanding_count"], 1)
        self.assertEqual(response.context["stats"]["overdue_total"], Decimal("110.000"))
        self.assertEqual(response.context["stats"]["overdue_count"], 1)
        self.assertContains(response, "1 unpaid invoices")

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
