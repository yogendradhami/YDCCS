from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import Notification


def invalidate_notification_count_cache(user):
    if user and user.pk:
        cache_key = f"notification-counts:{user.pk}:{timezone.now().date().isoformat()}"
        transaction.on_commit(lambda: cache.delete(cache_key))


def notify_user(user, title, message, notification_type="system", link=""):
    if not user or not user.pk:
        return

    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )
    invalidate_notification_count_cache(user)


def notify_admins(title, message, notification_type="system", link=""):
    admins = User.objects.filter(is_staff=True)
    for admin in admins:
        notify_user(admin, title, message, notification_type, link)
