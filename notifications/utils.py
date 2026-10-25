from contextlib import contextmanager
from threading import RLock
import weakref

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import Notification


_instance_flag_locks = {}
_instance_flag_locks_guard = RLock()
_unweakrefable_flag_lock = RLock()


def _get_instance_flag_lock(instance):
    instance_id = id(instance)
    try:
        weakref.ref(instance)
    except TypeError:
        return _unweakrefable_flag_lock

    with _instance_flag_locks_guard:
        existing = _instance_flag_locks.get(instance_id)
        if existing and existing[0]() is instance:
            return existing[1]

        lock = RLock()

        def discard_reference(reference):
            with _instance_flag_locks_guard:
                current = _instance_flag_locks.get(instance_id)
                if current and current[0] is reference:
                    _instance_flag_locks.pop(instance_id, None)

        reference = weakref.ref(instance, discard_reference)
        _instance_flag_locks[instance_id] = (reference, lock)
        return lock


@contextmanager
def temporary_instance_flags(instance, **flags):
    with _get_instance_flag_lock(instance):
        original = {
            name: (name in instance.__dict__, instance.__dict__.get(name))
            for name in flags
        }
        try:
            for name, value in flags.items():
                setattr(instance, name, value)
            yield
        finally:
            for name, (existed, value) in original.items():
                if existed:
                    setattr(instance, name, value)
                else:
                    instance.__dict__.pop(name, None)


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
