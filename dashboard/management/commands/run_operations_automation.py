from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from dashboard.operations_automation import run_operations_automation


class Command(BaseCommand):
    help = "Evaluate operational reminders and create idempotent management alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            help="Evaluate due dates against an ISO date (YYYY-MM-DD).",
        )

    def handle(self, *args, **options):
        as_of_value = options.get("as_of")
        as_of = parse_date(as_of_value) if as_of_value else None
        if as_of_value and not as_of:
            raise CommandError("--as-of must be a valid ISO date (YYYY-MM-DD).")

        result = run_operations_automation(as_of=as_of)
        self.stdout.write(
            self.style.SUCCESS(
                f"Operations checks completed for {result['as_of']}: "
                f"{result['events_created']} new events; "
                f"{result['duplicates_skipped']} duplicates skipped."
            )
        )
