import logging

from django.db import transaction
from django.db.models.signals import post_delete

from .models import QuoteImage


logger = logging.getLogger(__name__)


def cleanup_deleted_quote_image(sender, instance, using, **kwargs):
    image_name = instance.image.name
    storage = instance.image.storage
    if (
        not image_name
        or storage.__class__.__module__.startswith("cloudinary_storage.")
    ):
        return

    def delete_if_unreferenced():
        if QuoteImage._base_manager.using(using).filter(image=image_name).exists():
            return
        try:
            storage.delete(image_name)
        except Exception:
            logger.exception("Could not clean up deleted quote image %s.", image_name)

    transaction.on_commit(delete_if_unreferenced, using=using)


post_delete.connect(
    cleanup_deleted_quote_image,
    sender=QuoteImage,
    weak=False,
    dispatch_uid="quotes.cleanup-deleted-quote-image",
)
