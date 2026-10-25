import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from support.models import LiveChatConversation, LiveChatRateLimitBucket

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Report or delete closed live chats beyond the configured retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Report eligible records without deleting them (the default).",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually delete eligible conversations and their messages.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Maximum candidate conversations processed in one run.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size < 1 or batch_size > 5000:
            raise CommandError("--batch-size must be between 1 and 5000.")

        retention_days = settings.LIVE_CHAT_RETENTION_DAYS
        cutoff = timezone.now() - timedelta(days=retention_days)
        eligible = LiveChatConversation.objects.filter(
            status="closed",
            closed_at__isnull=False,
            closed_at__lte=cutoff,
            legal_hold=False,
        ).order_by("closed_at", "pk")
        candidate_ids = list(eligible.values_list("pk", flat=True)[:batch_size])
        eligible_count = eligible.count()

        self.stdout.write(
            f"Retention={retention_days} days; eligible={eligible_count}; "
            f"batch={len(candidate_ids)}; mode={'delete' if options['delete'] else 'dry-run'}."
        )

        deleted = 0
        failed = 0
        if options["delete"]:
            for conversation_id in candidate_ids:
                try:
                    with transaction.atomic():
                        conversation = (
                            LiveChatConversation.objects.select_for_update()
                            .filter(
                                pk=conversation_id,
                                status="closed",
                                closed_at__isnull=False,
                                closed_at__lte=cutoff,
                                legal_hold=False,
                            )
                            .first()
                        )
                        if conversation is not None:
                            conversation.delete()
                            deleted += 1
                except Exception:
                    failed += 1
                    logger.exception(
                        "Failed to delete expired live chat conversation %s.",
                        conversation_id,
                    )
            self.stdout.write(f"Deleted={deleted}; failed={failed}.")

        old_rate_limit_buckets = LiveChatRateLimitBucket.objects.filter(
            window_started_at__lt=timezone.now() - timedelta(days=2)
        )
        bucket_count = old_rate_limit_buckets.count()
        if not options["delete"]:
            self.stdout.write(f"Expired rate-limit buckets eligible={bucket_count}.")
        else:
            expired_bucket_ids = list(
                old_rate_limit_buckets.values_list("pk", flat=True)[:batch_size]
            )
            removed, _ = LiveChatRateLimitBucket.objects.filter(
                pk__in=expired_bucket_ids,
                window_started_at__lt=timezone.now() - timedelta(days=2),
            ).delete()
            self.stdout.write(f"Expired rate-limit buckets removed={removed}.")

        if failed:
            raise CommandError(
                f"Cleanup completed with {failed} failed conversation(s); inspect logs and retry."
            )
