import logging

from django.apps import apps
from django.db import transaction
from django.db.models import FileField
from django.db.models import Q

logger = logging.getLogger(__name__)


def _is_cloudinary_storage(storage):
    return any(
        cls.__module__.startswith("cloudinary_storage.")
        or (cls.__module__, cls.__name__)
        == ("core.storage", "CloudinaryVideoStorage")
        for cls in storage.__class__.__mro__
    )


def _cloudinary_file_fields():
    return [
        (model, field)
        for model in apps.get_models()
        for field in model._meta.concrete_fields
        if isinstance(field, FileField) and _is_cloudinary_storage(field.storage)
    ]


def is_cloudinary_asset_referenced(name, using="default"):
    fields_by_model = {}
    for model, field in _cloudinary_file_fields():
        fields_by_model.setdefault(model, []).append(field)

    for model, fields in fields_by_model.items():
        query = Q()
        for field in fields:
            query |= Q(**{field.name: name})
        if model._base_manager.using(using).filter(query).exists():
            return True
    return False


def delete_cloudinary_asset_if_unreferenced(storage, name, using="default"):
    if not name:
        return True
    if is_cloudinary_asset_referenced(name, using):
        logger.warning(
            "Skipped cleanup of Cloudinary asset %s because it is still attached to a record.",
            name,
        )
        return False
    try:
        result = storage.delete(name)
    except Exception:
        logger.exception("Could not delete unreferenced Cloudinary asset %s.", name)
        return False
    if result is False:
        logger.warning("Cloudinary did not confirm deletion of asset %s.", name)
        return False
    return True


def _schedule_cleanup(storage, name, using):
    if not name:
        return
    transaction.on_commit(
        lambda: delete_cloudinary_asset_if_unreferenced(storage, name, using),
        using=using,
    )


def track_cloudinary_file_changes(sender):
    fields = [
        field
        for field in sender._meta.concrete_fields
        if isinstance(field, FileField) and _is_cloudinary_storage(field.storage)
    ]
    if not fields:
        return

    def remember_previous_files(instance, using, **kwargs):
        if instance._state.adding or instance.pk is None:
            instance._previous_cloudinary_files = {}
            return
        previous = (
            sender._base_manager.using(using)
            .filter(pk=instance.pk)
            .values_list(*(field.attname for field in fields))
            .first()
        )
        instance._previous_cloudinary_files = (
            {
                field.attname: (field.storage, name)
                for field, name in zip(fields, previous)
                if name
            }
            if previous
            else {}
        )

    def clean_replaced_files(instance, using, **kwargs):
        previous = getattr(instance, "_previous_cloudinary_files", {})
        for field in fields:
            storage_and_name = previous.get(field.attname)
            if not storage_and_name:
                continue
            storage, old_name = storage_and_name
            new_name = getattr(instance, field.attname)
            if old_name != new_name:
                _schedule_cleanup(storage, old_name, using)
        instance._previous_cloudinary_files = {}

    def clean_deleted_files(instance, using, **kwargs):
        for field in fields:
            _schedule_cleanup(
                field.storage,
                getattr(instance, field.attname),
                using,
            )

    from django.db.models.signals import post_delete, post_save, pre_save

    pre_save.connect(
        remember_previous_files,
        sender=sender,
        weak=False,
        dispatch_uid=f"cloudinary-cleanup-before-save-{sender._meta.label_lower}",
    )
    post_save.connect(
        clean_replaced_files,
        sender=sender,
        weak=False,
        dispatch_uid=f"cloudinary-cleanup-after-save-{sender._meta.label_lower}",
    )
    post_delete.connect(
        clean_deleted_files,
        sender=sender,
        weak=False,
        dispatch_uid=f"cloudinary-cleanup-after-delete-{sender._meta.label_lower}",
    )


def connect_cloudinary_cleanup_signals():
    for model in apps.get_models():
        track_cloudinary_file_changes(model)
