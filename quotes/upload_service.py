import hmac
import logging
import secrets
import time
import uuid

import cloudinary
from cloudinary import api as cloudinary_api
from cloudinary import uploader as cloudinary_uploader
from cloudinary.utils import api_sign_request
from django.conf import settings
from django.core import signing


logger = logging.getLogger(__name__)

MAX_QUOTE_IMAGES = 6
MAX_QUOTE_IMAGE_SIZE = 15 * 1024 * 1024
MAX_QUOTE_IMAGE_TOTAL_SIZE = 60 * 1024 * 1024
QUOTE_IMAGE_FORMATS = frozenset(
    {
        "avif",
        "bmp",
        "gif",
        "heic",
        "heif",
        "jfif",
        "jpg",
        "jpeg",
        "png",
        "tif",
        "tiff",
        "webp",
    }
)
QUOTE_IMAGE_BATCH_TTL = 60 * 60
QUOTE_IMAGE_UPLOAD_SESSION_KEY = "quote_image_upload_batches"
QUOTE_IMAGE_BATCH_SALT = "quote-image-upload-batch"


def _configure_cloudinary():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
        api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
        api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
    )


def create_quote_image_batch(workflow_key, count):
    if not 1 <= count <= MAX_QUOTE_IMAGES:
        raise ValueError(f"Choose between 1 and {MAX_QUOTE_IMAGES} property photos.")

    timestamp = int(time.time())
    allowed_formats = ",".join(sorted(QUOTE_IMAGE_FORMATS))
    prefix = f"quote_images/{workflow_key[:24]}"
    public_ids = []
    uploads = []
    for _ in range(count):
        public_id = f"{prefix}/{uuid.uuid4().hex}"
        params = {
            "public_id": public_id,
            "timestamp": timestamp,
            "allowed_formats": allowed_formats,
        }
        uploads.append(
            {
                **params,
                "signature": api_sign_request(
                    params, settings.CLOUDINARY_STORAGE["API_SECRET"]
                ),
                "api_key": settings.CLOUDINARY_STORAGE["API_KEY"],
            }
        )
        public_ids.append(public_id)

    nonce = secrets.token_urlsafe(24)
    batch_token = signing.dumps(
        {"nonce": nonce, "workflow_key": workflow_key},
        salt=QUOTE_IMAGE_BATCH_SALT,
    )
    return {
        "nonce": nonce,
        "batch_token": batch_token,
        "public_ids": public_ids,
        "uploads": uploads,
    }


def load_quote_image_batch(batch_token, workflow_key):
    try:
        payload = signing.loads(
            batch_token,
            salt=QUOTE_IMAGE_BATCH_SALT,
            max_age=QUOTE_IMAGE_BATCH_TTL,
        )
    except (signing.BadSignature, TypeError):
        raise ValueError("The property photo upload batch expired or is invalid.")

    nonce = payload.get("nonce")
    if not isinstance(nonce, str) or not hmac.compare_digest(
        str(payload.get("workflow_key", "")), workflow_key
    ):
        raise ValueError("The property photo batch belongs to another quote form.")
    return nonce


def verify_quote_image_uploads(supplied_uploads, expected_ids):
    if (
        not isinstance(supplied_uploads, list)
        or not supplied_uploads
        or len(supplied_uploads) > MAX_QUOTE_IMAGES
        or len(supplied_uploads) != len(expected_ids)
    ):
        raise ValueError("The property photo upload batch is incomplete.")

    response_ids = []
    response_versions = {}
    secret = settings.CLOUDINARY_STORAGE["API_SECRET"]
    for result in supplied_uploads:
        if not isinstance(result, dict):
            raise ValueError("Cloudinary returned an invalid property photo receipt.")

        public_id = result.get("public_id", "")
        signature = result.get("signature", "")
        try:
            version = int(result.get("version"))
        except (TypeError, ValueError):
            raise ValueError("Cloudinary returned an invalid property photo version.")

        if (
            not isinstance(public_id, str)
            or not public_id.startswith("quote_images/")
            or version <= 0
        ):
            raise ValueError("The property photo does not belong to this upload.")

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
            raise ValueError("Cloudinary's property photo signature could not be verified.")

        response_ids.append(public_id)
        response_versions[public_id] = version

    if (
        len(set(response_ids)) != len(expected_ids)
        or set(response_ids) != set(expected_ids)
    ):
        raise ValueError("The uploaded property photos do not match the signed batch.")

    _configure_cloudinary()
    resources_response = cloudinary_api.resources_by_ids(
        list(expected_ids),
        resource_type="image",
        type="upload",
    )
    resources = resources_response.get("resources", [])
    if not isinstance(resources, list) or len(resources) != len(expected_ids):
        raise ValueError("Cloudinary returned duplicate or incomplete photo metadata.")
    resources_by_id = {
        resource.get("public_id"): resource
        for resource in resources
        if isinstance(resource, dict)
    }
    if set(resources_by_id) != set(expected_ids):
        raise ValueError("Cloudinary could not confirm every property photo.")

    total_bytes = 0
    for public_id, resource in resources_by_id.items():
        try:
            actual_bytes = int(resource.get("bytes", 0))
            actual_version = int(resource.get("version", 0))
        except (TypeError, ValueError):
            raise ValueError("Cloudinary returned incomplete property photo metadata.")
        actual_format = str(resource.get("format", "")).lower()
        if (
            resource.get("resource_type") != "image"
            or actual_format not in QUOTE_IMAGE_FORMATS
            or not 0 < actual_bytes <= MAX_QUOTE_IMAGE_SIZE
            or actual_version != response_versions[public_id]
        ):
            raise ValueError(
                "A property photo has an unsupported type or exceeds 15 MB."
            )
        total_bytes += actual_bytes

    if total_bytes > MAX_QUOTE_IMAGE_TOTAL_SIZE:
        raise ValueError("Property photos must total 60 MB or less.")
    return [{"public_id": public_id} for public_id in response_ids]


def destroy_quote_image_assets(public_ids):
    safe_ids = list(
        dict.fromkeys(
            public_id
            for public_id in public_ids
            if isinstance(public_id, str)
            and public_id.startswith("quote_images/")
        )
    )
    if not safe_ids:
        return

    _configure_cloudinary()
    for public_id in safe_ids:
        try:
            cloudinary_uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )
        except Exception:
            logger.exception("Could not clean up quote image asset %s", public_id)
