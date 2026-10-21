
from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.db import DatabaseError
from django.utils import timezone

from security_monitor.models import SecurityAlertDelivery
from security_monitor.notifications import send_security_alert

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BATCH_SIZE = 50


class Command(BaseCommand):
    help = "Process queued YDCCS security alert emails."

    def handle(self, *args, **options):
        now = timezone.now()

        try:
            deliveries = list(
                SecurityAlertDelivery.objects.filter(
                    status=SecurityAlertDelivery.Status.PENDING,
                    next_attempt_at__lte=now,
                )
                .select_related("finding")
                .order_by("created_at")[:BATCH_SIZE]
            )
        except DatabaseError:
            logger.exception(
                "Unable to load queued security alerts."
            )
            raise

        if not deliveries:
            self.stdout.write("No queued security alerts are due.")
            return

        for delivery in deliveries:
            try:
                sent = send_security_alert(delivery.finding)

                if not sent:
                    raise RuntimeError(
                        "Email backend did not confirm sending."
                    )

                delivery.status = SecurityAlertDelivery.Status.SENT
                delivery.sent_at = timezone.now()
                delivery.last_error = ""
                delivery.save(
                    update_fields=[
                        "status",
                        "sent_at",
                        "last_error",
                    ]
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Alert {delivery.pk} sent."
                    )
                )

            except Exception as exc:
                logger.exception(
                    "Security alert delivery %s failed.",
                    delivery.pk,
                )

                delivery.attempts += 1
                delivery.last_error = (
                    f"{type(exc).__name__}: alert delivery failed"
                )[:1000]

                if delivery.attempts >= MAX_ATTEMPTS:
                    delivery.status = (
                        SecurityAlertDelivery.Status.FAILED
                    )
                else:
                    delay_minutes = min(
                        2 ** delivery.attempts,
                        60,
                    )
                    delivery.next_attempt_at = (
                        timezone.now()
                        + timedelta(minutes=delay_minutes)
                    )

                delivery.save(
                    update_fields=[
                        "attempts",
                        "last_error",
                        "status",
                        "next_attempt_at",
                    ]
                )

        self.stdout.write("Security alert queue processing finished.")
