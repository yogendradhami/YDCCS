
import logging

from django.core.management.base import BaseCommand

from security_monitor.audits import (
    audit_django_configuration,
    audit_public_website,
)
from security_monitor.notifications import send_security_report

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the YDCCS scheduled security audit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report",
            action="store_true",
            help="Email a report after the audit.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting YDCCS security audit...")

        # Isolate failures so one check does not prevent the next.
        checks = [
            ("Public website", audit_public_website),
            ("Django configuration", audit_django_configuration),
        ]

        for label, check in checks:
            try:
                check()
                self.stdout.write(self.style.SUCCESS(f"{label}: completed"))
            except Exception:
                logger.exception("Security audit check failed: %s", label)
                self.stderr.write(f"{label}: failed; check worker logs.")

        if options["report"]:
            if send_security_report():
                self.stdout.write(
                    self.style.SUCCESS("Security report email sent.")
                )
            else:
                self.stderr.write(
                    "Security report email was not confirmed as sent."
                )

        self.stdout.write("Security audit finished.")
