from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .models import GalleryImage

logger = logging.getLogger(__name__)


def save_gallery_uploads(gallery_item, primary_files, additional_files):
    """Store gallery media with bounded concurrency, then persist its rows."""
    uploads = []
    for field_name, uploaded_file in primary_files.items():
        if isinstance(uploaded_file, UploadedFile):
            field = gallery_item._meta.get_field(field_name)
            instance = gallery_item
            uploads.append((field_name, field, instance, uploaded_file))

    extra_field = GalleryImage._meta.get_field("image")
    for uploaded_file in additional_files:
        if isinstance(uploaded_file, UploadedFile):
            uploads.append(("additional_images", extra_field, GalleryImage(gallery=gallery_item), uploaded_file))

    if not uploads:
        with transaction.atomic():
            gallery_item.save()
        return gallery_item

    def store(upload):
        _field_name, field, instance, uploaded_file = upload
        uploaded_file.seek(0)
        filename = field.generate_filename(instance, uploaded_file.name)
        return field.storage.save(filename, uploaded_file)

    stored_names = [None] * len(uploads)
    failures = []
    with ThreadPoolExecutor(max_workers=min(3, len(uploads))) as executor:
        futures = {
            executor.submit(store, upload): index
            for index, upload in enumerate(uploads)
        }
        for future in as_completed(futures):
            try:
                stored_names[futures[future]] = future.result()
            except Exception as exc:
                failures.append(exc)

    if failures:
        _delete_stored_uploads(uploads, stored_names)
        raise failures[0]

    try:
        additional_names = []
        with transaction.atomic():
            for upload, stored_name in zip(uploads, stored_names):
                field_name = upload[0]
                if field_name == "additional_images":
                    additional_names.append(stored_name)
                else:
                    setattr(gallery_item, field_name, stored_name)

            gallery_item.save()
            if additional_names:
                GalleryImage.objects.bulk_create(
                    [GalleryImage(gallery=gallery_item, image=name) for name in additional_names],
                    batch_size=20,
                )
    except Exception:
        _delete_stored_uploads(uploads, stored_names)
        raise

    return gallery_item


def _delete_stored_uploads(uploads, stored_names):
    for upload, name in zip(uploads, stored_names):
        if not name:
            continue
        try:
            upload[1].storage.delete(name)
        except Exception:
            logger.exception("Could not clean up gallery upload %s", name)
