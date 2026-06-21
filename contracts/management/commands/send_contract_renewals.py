from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from contracts.models import CleaningContract
from dashboard.models import EmailLog


class Command(BaseCommand):
    help = "Send automatic contract renewal reminders"

    def handle(self, *args, **kwargs):

        today = timezone.localdate()

        contracts = CleaningContract.objects.filter(
            status="active", end_date__isnull=False
        )

        sent_count = 0

        for contract in contracts:

            days_left = (contract.end_date - today).days

            reminder_type = None

            if days_left <= 30 and not contract.renewal_30_sent:
                reminder_type = "30"

            if days_left <= 14 and not contract.renewal_14_sent:
                reminder_type = "14"

            if days_left <= 7 and not contract.renewal_7_sent:
                reminder_type = "7"

            if not reminder_type:
                continue

            customer = contract.customer

            if not customer.email:
                continue

            subject = f"Contract Renewal Reminder ({days_left} days remaining)"

            message = f"""
Dear {customer.full_name},

Your cleaning contract will expire on:

{contract.end_date}

Please contact YD Commercial Cleaning Services to renew your agreement.

Thank you.
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                email_type="contract_renewal",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=f"Contract #{contract.id}",
            )

            if reminder_type == "30":
                contract.renewal_30_sent = True

            elif reminder_type == "14":
                contract.renewal_14_sent = True

            elif reminder_type == "7":
                contract.renewal_7_sent = True

            contract.save()

            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"{sent_count} renewal emails sent."))
