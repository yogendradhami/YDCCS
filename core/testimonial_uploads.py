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


logger = logging.getLogger(__name__)

TESTIMONIAL_UPLOAD_SESSION_KEY = "pending_testimonial_video_uploads"
TESTIMONIAL_UPLOAD_PREFIX = "testimonial-videos/admin"
TESTIMONIAL_UPLOAD_TTL_SECONDS = 60 * 60
MAX_TESTIMONIAL_VIDEO_BYTES = 100 * 1024 * 1024
ALLOWED_TESTIMONIAL_VIDEO_FORMATS = frozenset(
    {"mp4", "mov", "m4v", "webm", "avi", "mkv", "mpeg", "mpg", "ogv", "3gp"}
)


def _configure_cloudinary():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
        api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
        api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
    )


def create_testimonial_upload(*, user_id, item_id=None):
    _configure_cloudinary()
    nonce = secrets.token_urlsafe(24)
    public_id = f"{TESTIMONIAL_UPLOAD_PREFIX}/{nonce}/{uuid.uuid4().hex}"
    timestamp = int(time.time())
    allowed_formats = ",".join(sorted(ALLOWED_TESTIMONIAL_VIDEO_FORMATS))
    signature = api_sign_request(
        {
            "public_id": public_id,
            "timestamp": timestamp,
            "allowed_formats": allowed_formats,
            "overwrite": "false",
        },
        settings.CLOUDINARY_STORAGE["API_SECRET"],
    )
    return nonce, {
        "user_id": user_id,
        "item_id": item_id,
        "public_id": public_id,
        "timestamp": timestamp,
        "allowed_formats": allowed_formats,
        "expires_at": timestamp + TESTIMONIAL_UPLOAD_TTL_SECONDS,
        "finalized": False,
    }, {
        "public_id": public_id,
        "timestamp": timestamp,
        "allowed_formats": allowed_formats,
        "overwrite": "false",
        "api_key": settings.CLOUDINARY_STORAGE["API_KEY"],
        "signature": signature,
        "max_file_bytes": MAX_TESTIMONIAL_VIDEO_BYTES,
    }


def _resource_for_expected_upload(batch):
    _configure_cloudinary()
    response = cloudinary_api.resources_by_ids(
        [batch["public_id"]],
        resource_type="video",
        type="upload",
    )
    resources = response.get("resources", [])
    matching = [
        resource
        for resource in resources
        if isinstance(resource, dict)
        and resource.get("public_id") == batch["public_id"]
    ]
    if len(matching) != 1:
        return None
    return matching[0]


def verify_testimonial_upload_receipt(batch, receipt):
    if not isinstance(receipt, dict):
        raise ValueError("Cloudinary returned an invalid video receipt.")
    public_id = receipt.get("public_id")
    signature = receipt.get("signature")
    try:
        version = int(receipt.get("version"))
    except (TypeError, ValueError):
        raise ValueError("Cloudinary returned an invalid video version.")

    expected_id = batch.get("public_id", "")
    if (
        not isinstance(public_id, str)
        or public_id != expected_id
        or not public_id.startswith(f"{TESTIMONIAL_UPLOAD_PREFIX}/")
        or version <= 0
    ):
        raise ValueError("The uploaded video does not belong to this upload batch.")

    expected_signature = api_sign_request(
        {"public_id": public_id, "version": version},
        settings.CLOUDINARY_STORAGE["API_SECRET"],
        signature_version=1,
    )
    if (
        not isinstance(signature, str)
        or not signature.isascii()
        or not hmac.compare_digest(signature, expected_signature)
    ):
        raise ValueError("Cloudinary's video signature could not be verified.")

    resource = _resource_for_expected_upload(batch)
    if resource is None:
        raise ValueError("Cloudinary could not confirm the uploaded video.")
    try:
        actual_bytes = int(resource.get("bytes", 0))
        actual_version = int(resource.get("version", 0))
    except (TypeError, ValueError):
        raise ValueError("Cloudinary returned incomplete video metadata.")
    actual_format = str(resource.get("format", "")).lower()
    if (
        resource.get("resource_type") != "video"
        or resource.get("type") != "upload"
        or not public_id.startswith(f"{TESTIMONIAL_UPLOAD_PREFIX}/")
        or actual_format not in ALLOWED_TESTIMONIAL_VIDEO_FORMATS
        or not 0 < actual_bytes <= MAX_TESTIMONIAL_VIDEO_BYTES
        or actual_version != version
    ):
        raise ValueError("The video format or file size is not supported.")

    return {"public_id": public_id, "version": version, "bytes": actual_bytes}


def cleanup_testimonial_upload(batch):
    """Delete only the exact, verified video asset named by this upload batch."""
    public_id = batch.get("public_id", "") if isinstance(batch, dict) else ""
    if (
        not isinstance(public_id, str)
        or not public_id.startswith(f"{TESTIMONIAL_UPLOAD_PREFIX}/")
    ):
        return False
    try:
        resource = _resource_for_expected_upload(batch)
        if resource is None:
            return True
        if (
            resource.get("resource_type") != "video"
            or resource.get("type") != "upload"
            or resource.get("public_id") != public_id
        ):
            logger.error("Refusing to delete unverified testimonial asset %s.", public_id)
            return False
        result = cloudinary_uploader.destroy(
            public_id,
            resource_type="video",
            invalidate=True,
        )
        return result.get("result") in {"ok", "not found"}
    except Exception:
        logger.exception("Could not clean up testimonial video upload %s.", public_id)
        return False
