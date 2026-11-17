import logging

from django.core.management.base import BaseCommand, CommandError

from google_reviews.business_profile import (
    GoogleBusinessProfileError,
    GoogleBusinessProfileService,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronise Google Business Profile reviews into the YDCCS database."

    def handle(self, *args, **options):
        self.stdout.write("Starting Google Reviews synchronisation...")

        try:
            saved, retrieved = (
                GoogleBusinessProfileService().sync_selected_reviews()
            )
        except GoogleBusinessProfileError as exc:
            logger.exception("Google Business Profile review sync failed.")
            raise CommandError(exc.user_message) from exc
        except Exception as exc:
            logger.exception("Unexpected Google Reviews synchronisation error.")
            raise CommandError(
                "Google Reviews synchronisation failed. Check the worker logs."
            ) from exc

        if retrieved == 0:
            self.stdout.write(
                self.style.WARNING(
                    "Google returned zero reviews. Existing saved reviews "
                    "were left unchanged."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Google Reviews synchronisation completed. "
                    f"Retrieved {retrieved}; saved {saved}."
                )
            )

        self.stdout.write("Google Reviews synchronisation finished.")