from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from induction.models import EmployeeInduction, InductionExpiryReminder
from notifications.utils import notify_user


class Command(BaseCommand):
    help = (
        "Send idempotent employee portal and email reminders for induction "
        "expiry 30 days and 7 days beforehand, and on the expiry date."
    )

    def handle(self, *args, **options):
        today = timezone.localdate()
        created_count = 0
        portal_count = 0
        email_count = 0
        skipped_portal_count = 0
        skipped_email_count = 0

        inductions = (
            EmployeeInduction.objects.filter(
                status="completed",
                expires_on__isnull=False,
                expires_on__lte=today + timedelta(days=30),
            )
            .select_related("employee__user")
            .order_by("expires_on", "pk")
        )
        for induction in inductions:
            days_remaining = (induction.expires_on - today).days
            if days_remaining > 7:
                days_before_expiry = 30
            elif days_remaining > 0:
                days_before_expiry = 7
            else:
                days_before_expiry = 0

            reminder, created = InductionExpiryReminder.objects.get_or_create(
                induction=induction,
                expiry_date=induction.expires_on,
                days_before_expiry=days_before_expiry,
            )
            created_count += int(created)
            employee = induction.employee
            employee_user = employee.user
            reminder_date = induction.expires_on.strftime("%d %B %Y")
            if days_before_expiry:
                title = "Induction renewal reminder"
                message = (
                    f"Your induction will expire on {reminder_date} "
                    f"(in {days_remaining} days). "
                    "Please review your employee learning portal and arrange "
                    "your renewal with your supervisor."
                )
                subject = (
                    f"YD Cleaning induction expires in {days_remaining} days"
                )
            else:
                title = "Your induction is due for renewal"
                message = (
                    f"Your induction reached its expiry date ({reminder_date}). "
                    "Please complete the renewal modules in your employee "
                    "learning portal."
                )
                subject = "YD Cleaning induction renewal is due"

            if reminder.portal_status == "pending":
                if employee_user:
                    notify_user(
                        employee_user,
                        title,
                        message,
                        "employee",
                        "/employee/induction/",
                    )
                    reminder.portal_status = "sent"
                    reminder.portal_sent_at = timezone.now()
                    reminder.save(
                        update_fields=["portal_status", "portal_sent_at"]
                    )
                    portal_count += 1
                else:
                    reminder.portal_status = "skipped"
                    reminder.save(update_fields=["portal_status"])
                    skipped_portal_count += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipped portal reminder for induction #{induction.pk}: "
                            "employee has no linked portal user."
                        )
                    )

            if reminder.email_status == "pending":
                recipient = (
                    (employee_user.email if employee_user else "")
                    or employee.email
                )
                if not recipient:
                    reminder.email_status = "skipped"
                    reminder.save(update_fields=["email_status"])
                    skipped_email_count += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipped email reminder for induction #{induction.pk}: "
                            "employee has no email address."
                        )
                    )
                    continue

                sent = send_mail(
                    subject=subject,
                    message=(
                        f"Hello {employee.full_name},\n\n{message}\n\n"
                        "Sign in to your employee portal to review your "
                        "induction and contact your supervisor if you need help."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                if sent != 1:
                    raise CommandError(
                        f"Email backend did not confirm delivery to {recipient}."
                    )
                reminder.email_status = "sent"
                reminder.email_sent_at = timezone.now()
                reminder.save(update_fields=["email_status", "email_sent_at"])
                email_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Expiry reminders checked: {created_count} records created, "
                f"{portal_count} portal notices sent, {email_count} emails sent, "
                f"{skipped_portal_count} portal and {skipped_email_count} email "
                "reminders skipped."
            )
        )
