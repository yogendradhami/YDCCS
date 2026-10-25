from datetime import datetime, timezone as datetime_timezone
import hashlib
import hmac

from django.conf import settings
from django.db import transaction

from .models import LiveChatRateLimitBucket


def allow_live_chat_action(identity, action, limit, window_seconds=60):
    epoch_window = int(datetime.now(datetime_timezone.utc).timestamp()) // window_seconds
    material = f"{action}:{identity}:{epoch_window}".encode()
    key = hmac.new(
        settings.SECRET_KEY.encode(),
        material,
        hashlib.sha256,
    ).hexdigest()

    with transaction.atomic():
        LiveChatRateLimitBucket.objects.get_or_create(
            key=key,
            defaults={
                "window_started_at": datetime.fromtimestamp(
                    epoch_window * window_seconds,
                    tz=datetime_timezone.utc,
                ),
                "count": 0,
            },
        )
        bucket = LiveChatRateLimitBucket.objects.select_for_update().get(key=key)
        if bucket.count >= limit:
            return False
        bucket.count += 1
        bucket.save(update_fields=["count"])
    return True
