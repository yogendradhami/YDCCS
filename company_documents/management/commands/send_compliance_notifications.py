from django.core.management.base import BaseCommand

from company_documents.services.compliance_notifications import (
    get_compliance_document_alerts,
    get_missing_compliance_alerts,
)
from company_documents.services.compliance_notification_dispatcher import (
    dispatch_compliance_notifications,
    get_compliance_recipients,
)


class Command(BaseCommand):
    help = (
        "Create persistent in-app notifications for "
        "company document and compliance alerts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Show what would be created "
                "without saving notifications."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        document_alerts = get_compliance_document_alerts()
        missing_alerts = get_missing_compliance_alerts()
        recipients = list(get_compliance_recipients())

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN — no notifications will be created."
                )
            )

            self.stdout.write("")

            self.stdout.write(
                f"Document alerts: {len(document_alerts)}"
            )

            self.stdout.write(
                f"Missing compliance alerts: "
                f"{len(missing_alerts)}"
            )

            self.stdout.write(
                f"Total alerts: "
                f"{len(document_alerts) + len(missing_alerts)}"
            )

            self.stdout.write(
                f"Recipients: {len(recipients)}"
            )

            self.stdout.write("")

            if document_alerts:
                self.stdout.write(
                    self.style.HTTP_INFO(
                        "DOCUMENT ALERTS"
                    )
                )

                for alert in document_alerts:
                    document = alert["document"]

                    self.stdout.write(
                        f"- [{alert['severity'].upper()}] "
                        f"{alert['title']} — "
                        f"{document.name or document.original_filename}"
                    )

            if missing_alerts:
                self.stdout.write("")

                self.stdout.write(
                    self.style.HTTP_INFO(
                        "MISSING REQUIREMENTS"
                    )
                )

                for alert in missing_alerts:
                    self.stdout.write(
                        f"- [{alert['scope_label']}] "
                        f"{alert['entity_name']} — "
                        f"{alert['requirement_count']} missing"
                    )

                    for requirement in alert["requirements"]:
                        self.stdout.write(
                            f"    • {requirement}"
                        )

            return

        result = dispatch_compliance_notifications()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Compliance notification dispatch completed."
            )
        )

        self.stdout.write(
            f"Document alerts found: "
            f"{result['document_alerts_found']}"
        )

        self.stdout.write(
            f"Missing compliance alerts found: "
            f"{result['missing_alerts_found']}"
        )

        self.stdout.write(
            f"Total alerts found: "
            f"{result['alerts_found']}"
        )

        self.stdout.write(
            f"Recipients: "
            f"{result['recipients']}"
        )

        self.stdout.write(
            f"Notifications created: "
            f"{result['notifications_created']}"
        )

        self.stdout.write(
            f"Duplicates skipped: "
            f"{result['duplicates_skipped']}"
        )

        self.stdout.write(
            f"Notification centre: "
            f"{result['notification_center_url']}"
        )