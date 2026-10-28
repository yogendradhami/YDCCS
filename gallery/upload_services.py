from concurrent.futures import ThreadPoolExecutor, as_completed
import hmac
import logging
import secrets
import time
import uuid

import cloudinary
import cloudinary.api as cloudinary_api
import cloudinary.uploader as cloudinary_uploader
from cloudinary.utils import api_sign_request
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from core.media_cleanup import is_cloudinary_asset_referenced
from .forms import MAX_GALLERY_BATCH_SIZE, MAX_GALLERY_IMAGE_SIZE
from .models import GalleryImage, GalleryItem

logger = logging.getLogger(__name__)

GALLERY_UPLOAD_SESSION_KEY = "pending_gallery_upload_batches"
GALLERY_UPLOAD_PREFIX = "gallery/admin"
MAX_GALLERY_IMAGES = 23
MAX_ADDITIONAL_IMAGES = 20
GALLERY_BATCH_TTL_SECONDS = 60 * 60
ALLOWED_GALLERY_FORMATS = frozenset(
    {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"}
)
PRIMARY_GALLERY_SLOTS = frozenset({"image", "before_image", "after_image"})


def _configure_cloudinary():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
        api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
        api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
    )


def _validate_gallery_slots(slots, item_id=None):
    if not isinstance(slots, list) or not 1 <= len(slots) <= MAX_GALLERY_IMAGES:
        raise ValueError(f"Choose between 1 and {MAX_GALLERY_IMAGES} images.")
    if any(
        not isinstance(slot, str)
        or (slot not in PRIMARY_GALLERY_SLOTS and slot != "additional_images")
        for slot in slots
    ):
        raise ValueError("The upload batch contains an invalid gallery image slot.")
    for primary_slot in PRIMARY_GALLERY_SLOTS:
        if slots.count(primary_slot) > 1:
            raise ValueError("A primary gallery image slot can only be uploaded once.")

    additional_count = slots.count("additional_images")
    existing_count = (
        GalleryImage.objects.filter(gallery_id=item_id).count()
        if item_id is not None
        else 0
    )
    if additional_count + existing_count > MAX_ADDITIONAL_IMAGES:
        raise ValueError(
            f"A gallery item can contain no more than {MAX_ADDITIONAL_IMAGES} "
            "additional images."
        )


def _delete_gallery_assets(public_ids):
    public_ids = list(dict.fromkeys(public_ids))
    if not public_ids:
        return True
    _configure_cloudinary()
    cleaned = True
    for public_id in public_ids:
        if is_cloudinary_asset_referenced(public_id):
            logger.warning("Skipped cleanup of attached gallery asset %s.", public_id)
            cleaned = False
            continue
        try:
            result = cloudinary_uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )
            if result.get("result") not in {"ok", "not found"}:
                cleaned = False
        except Exception:
            cleaned = False
            logger.exception(
                "Could not clean up unclaimed gallery image %s.",
                public_id,
            )
    return cleaned


def create_gallery_upload_batch(slots, *, user_id, item_id=None):
    """Create one session-bound batch of server-named Cloudinary assets."""
    _validate_gallery_slots(slots, item_id=item_id)
    _configure_cloudinary()
    timestamp = int(time.time())
    nonce = secrets.token_urlsafe(24)
    allowed_formats = ",".join(sorted(ALLOWED_GALLERY_FORMATS))
    uploads = []
    expected = []

    for slot in slots:
        public_id = f"{GALLERY_UPLOAD_PREFIX}/{nonce}/{uuid.uuid4().hex}"
        params = {
            "public_id": public_id,
            "timestamp": timestamp,
            "allowed_formats": allowed_formats,
        }
        uploads.append(
            {
                "slot": slot,
                "public_id": public_id,
                "timestamp": timestamp,
                "allowed_formats": allowed_formats,
                "api_key": settings.CLOUDINARY_STORAGE["API_KEY"],
                "signature": api_sign_request(
                    params,
                    settings.CLOUDINARY_STORAGE["API_SECRET"],
                ),
            }
        )
        expected.append({"slot": slot, "public_id": public_id})

    return nonce, expected, uploads


def verify_gallery_upload_receipts(receipts, expected):
    """Verify signed Cloudinary receipts and authoritative image metadata."""
    if (
        not isinstance(receipts, list)
        or not isinstance(expected, list)
        or not expected
        or len(receipts) != len(expected)
        or len(expected) > MAX_GALLERY_IMAGES
    ):
        raise ValueError("The gallery image upload batch is incomplete.")

    expected_by_id = {
        entry["public_id"]: entry["slot"]
        for entry in expected
        if isinstance(entry, dict)
        and isinstance(entry.get("public_id"), str)
        and entry["public_id"].startswith(f"{GALLERY_UPLOAD_PREFIX}/")
    }
    if len(expected_by_id) != len(expected):
        raise ValueError("The signed gallery upload batch is invalid.")

    response_versions = {}
    response_ids = []
    secret = settings.CLOUDINARY_STORAGE["API_SECRET"]
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("Cloudinary returned an invalid gallery image receipt.")
        public_id = receipt.get("public_id")
        signature = receipt.get("signature")
        try:
            version = int(receipt.get("version"))
        except (TypeError, ValueError):
            raise ValueError("Cloudinary returned an invalid gallery image version.")

        if (
            not isinstance(public_id, str)
            or public_id not in expected_by_id
            or version <= 0
        ):
            raise ValueError("An uploaded image does not belong to this gallery batch.")

        expected_signature = api_sign_request(
            {"public_id": public_id, "version": version},
            secret,
            signature_version=1,
        )
        if (
            not isinstance(signature, str)
            or not signature.isascii()
            or not hmac.compare_digest(signature, expected_signature)
        ):
            raise ValueError("Cloudinary's gallery image signature could not be verified.")
        response_ids.append(public_id)
        response_versions[public_id] = version

    if len(set(response_ids)) != len(expected_by_id) or set(response_ids) != set(
        expected_by_id
    ):
        raise ValueError("Uploaded images do not match the signed gallery batch.")

    _configure_cloudinary()
    response = cloudinary_api.resources_by_ids(
        list(expected_by_id),
        resource_type="image",
        type="upload",
    )
    resources = response.get("resources", [])
    resources_by_id = {
        resource.get("public_id"): resource
        for resource in resources
        if isinstance(resource, dict)
    }
    if set(resources_by_id) != set(expected_by_id):
        raise ValueError("Cloudinary could not confirm every gallery image.")

    total_bytes = 0
    for public_id, resource in resources_by_id.items():
        try:
            actual_bytes = int(resource.get("bytes", 0))
            actual_version = int(resource.get("version", 0))
        except (TypeError, ValueError):
            raise ValueError("Cloudinary returned incomplete gallery image metadata.")
        actual_format = str(resource.get("format", "")).lower()
        total_bytes += actual_bytes
        if (
            resource.get("resource_type") != "image"
            or resource.get("type") != "upload"
            or actual_format not in ALLOWED_GALLERY_FORMATS
            or not 0 < actual_bytes <= MAX_GALLERY_IMAGE_SIZE
            or actual_version != response_versions[public_id]
        ):
            raise ValueError(
                "A gallery image has an unsupported format or exceeds 20 MB."
            )
    if total_bytes > MAX_GALLERY_BATCH_SIZE:
        raise ValueError("The gallery upload batch exceeds the 200 MB total limit.")

    return [
        {"slot": expected_by_id[public_id], "public_id": public_id}
        for public_id in response_ids
    ]


def save_verified_gallery_uploads(gallery_item, verified_assets):
    """Attach already-verified Cloudinary public IDs without re-uploading bytes."""
    if not isinstance(verified_assets, list) or not verified_assets:
        raise ValueError("The gallery upload batch is incomplete.")

    slots = [entry.get("slot") for entry in verified_assets if isinstance(entry, dict)]
    public_ids = [
        entry.get("public_id") for entry in verified_assets if isinstance(entry, dict)
    ]
    _validate_gallery_slots(slots, item_id=gallery_item.pk)
    if (
        len(slots) != len(verified_assets)
        or len(set(public_ids)) != len(public_ids)
        or any(
            not isinstance(public_id, str)
            or not public_id.startswith(f"{GALLERY_UPLOAD_PREFIX}/")
            for public_id in public_ids
        )
    ):
        raise ValueError("The gallery upload batch is invalid.")

    try:
        with transaction.atomic():
            additional_ids = []
            for entry in verified_assets:
                slot = entry["slot"]
                public_id = entry["public_id"]
                if slot == "additional_images":
                    additional_ids.append(public_id)
                else:
                    setattr(gallery_item, slot, public_id)

            gallery_item.save()
            if additional_ids:
                GalleryImage.objects.bulk_create(
                    [
                        GalleryImage(gallery=gallery_item, image=public_id)
                        for public_id in additional_ids
                    ],
                    batch_size=MAX_ADDITIONAL_IMAGES,
                )
    except Exception:
        _delete_gallery_assets(public_ids)
        raise

    return gallery_item

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
