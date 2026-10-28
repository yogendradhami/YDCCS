# Create your views here.
from collections import defaultdict
import json
import logging
import time

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from dashboard.decorators import admin_required
from .models import GalleryItem
from .upload_services import (
    GALLERY_BATCH_TTL_SECONDS,
    GALLERY_UPLOAD_SESSION_KEY,
    MAX_GALLERY_BATCH_SIZE,
    MAX_GALLERY_IMAGE_SIZE,
    _delete_gallery_assets,
    create_gallery_upload_batch,
    verify_gallery_upload_receipts,
)

logger = logging.getLogger(__name__)


def _gallery_batch_item_id(raw_item_id):
    if raw_item_id in (None, ""):
        return None
    try:
        item_id = int(raw_item_id)
    except (TypeError, ValueError):
        raise ValueError("The gallery item identifier is invalid.")
    if item_id <= 0:
        raise ValueError("The gallery item identifier is invalid.")
    return item_id


def _require_gallery_item_permission(request, item_id):
    permission = "gallery.add_galleryitem" if item_id is None else "gallery.change_galleryitem"
    if not request.user.has_perm(permission):
        raise PermissionDenied


def _get_gallery_upload_batch(request, nonce):
    batches = request.session.get(GALLERY_UPLOAD_SESSION_KEY, {})
    batch = batches.get(nonce)
    if (
        not batch
        or batch.get("user_id") != request.user.pk
        or batch.get("expires_at", 0) <= int(time.time())
    ):
        return batches, None
    return batches, batch


@login_required
@admin_required
@require_POST
def gallery_upload_batch(request):
    """Sign, finalize, or cancel an authenticated dashboard gallery upload."""
    action = request.POST.get("upload_action", "")
    batches = request.session.get(GALLERY_UPLOAD_SESSION_KEY, {})
    now = int(time.time())

    expired_ids = []
    for batch_nonce, batch in list(batches.items()):
        if batch.get("expires_at", 0) <= now:
            expired_ids.extend(
                entry.get("public_id", "")
                for entry in batch.get("expected", [])
                if isinstance(entry, dict)
            )
            batches.pop(batch_nonce, None)
    if expired_ids:
        _delete_gallery_assets(expired_ids)

    if action == "sign":
        try:
            slots = json.loads(request.POST.get("slots", ""))
            item_id = _gallery_batch_item_id(request.POST.get("item_id"))
            if item_id is not None:
                get_object_or_404(GalleryItem, pk=item_id)
            _require_gallery_item_permission(request, item_id)
            nonce, expected, uploads = create_gallery_upload_batch(
                slots,
                user_id=request.user.pk,
                item_id=item_id,
            )
        except ValueError as exc:
            request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
            return JsonResponse({"error": str(exc)}, status=400)

        batches[nonce] = {
            "expected": expected,
            "item_id": item_id,
            "user_id": request.user.pk,
            "expires_at": now + GALLERY_BATCH_TTL_SECONDS,
            "finalized": False,
        }
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse(
            {
                "cloud_name": settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                "nonce": nonce,
                "uploads": uploads,
                "max_file_bytes": MAX_GALLERY_IMAGE_SIZE,
                "max_batch_bytes": MAX_GALLERY_BATCH_SIZE,
            }
        )

    if action == "remove_saved":
        try:
            item_id = _gallery_batch_item_id(request.POST.get("item_id"))
            if item_id is None:
                raise ValueError("The gallery item identifier is required.")
            _require_gallery_item_permission(request, item_id)
            item = get_object_or_404(GalleryItem, pk=item_id)
            slot = request.POST.get("slot", "")
            if slot in {"image", "before_image", "after_image"}:
                if not getattr(item, slot).name:
                    raise ValueError("This gallery image is no longer available.")
                setattr(item, slot, None)
                item.save(update_fields=[slot])
            elif slot == "additional_images":
                try:
                    image_id = int(request.POST.get("image_id", ""))
                except (TypeError, ValueError):
                    raise ValueError("The additional gallery image identifier is invalid.")
                image = get_object_or_404(
                    item.additional_images,
                    pk=image_id,
                )
                image.delete()
            else:
                raise ValueError("The gallery image field is invalid.")
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse({"removed": True})

    nonce = request.POST.get("nonce", "")
    batches, batch = _get_gallery_upload_batch(request, nonce)
    if action == "cancel":
        if batch:
            try:
                item_id = _gallery_batch_item_id(request.POST.get("item_id"))
                if item_id != batch["item_id"]:
                    raise ValueError("The upload batch belongs to another gallery item.")
                _require_gallery_item_permission(request, batch["item_id"])
            except ValueError as exc:
                request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
                return JsonResponse({"error": str(exc)}, status=400)
            _delete_gallery_assets(
                [
                    entry["public_id"]
                    for entry in batch["expected"]
                ]
            )
            batches.pop(nonce, None)
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse({"cancelled": True})

    if action == "remove":
        if not batch:
            return JsonResponse(
                {"error": "The gallery upload batch expired or is unavailable."},
                status=400,
            )
        try:
            item_id = _gallery_batch_item_id(request.POST.get("item_id"))
            _require_gallery_item_permission(request, batch["item_id"])
            if item_id != batch["item_id"]:
                raise ValueError("The upload batch belongs to another gallery item.")
            if not batch.get("finalized"):
                raise ValueError("Images can only be removed after upload verification.")
            public_id = request.POST.get("public_id", "")
            expected_ids = {
                entry.get("public_id")
                for entry in batch.get("expected", [])
                if isinstance(entry, dict)
            }
            verified_ids = {
                entry.get("public_id")
                for entry in batch.get("verified_assets", [])
                if isinstance(entry, dict)
            }
            if (
                not isinstance(public_id, str)
                or public_id not in expected_ids
                or public_id not in verified_ids
                or not public_id.startswith(f"gallery/admin/{nonce}/")
            ):
                raise ValueError("The image does not belong to this upload batch.")
        except ValueError as exc:
            request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
            return JsonResponse({"error": str(exc)}, status=400)

        if not _delete_gallery_assets([public_id]):
            request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
            return JsonResponse(
                {"error": "The staged image could not be safely removed. Please retry."},
                status=502,
            )
        batch["expected"] = [
            entry for entry in batch["expected"] if entry["public_id"] != public_id
        ]
        batch["verified_assets"] = [
            entry
            for entry in batch["verified_assets"]
            if entry["public_id"] != public_id
        ]
        remaining = len(batch["verified_assets"])
        if remaining:
            batches[nonce] = batch
        else:
            batches.pop(nonce, None)
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse({"removed": True, "remaining": remaining})

    if action != "finalize":
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse({"error": "Unsupported gallery upload action."}, status=400)
    if not batch:
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse(
            {"error": "The gallery upload batch expired or is unavailable."},
            status=400,
        )

    try:
        item_id = _gallery_batch_item_id(request.POST.get("item_id"))
        _require_gallery_item_permission(request, batch["item_id"])
        if item_id != batch["item_id"]:
            raise ValueError("The upload batch belongs to another gallery item.")
        if batch.get("finalized"):
            raise ValueError("This gallery upload batch was already finalized.")
        receipts = json.loads(request.POST.get("receipts", ""))
        verified_assets = verify_gallery_upload_receipts(
            receipts,
            batch["expected"],
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        _delete_gallery_assets(
            [entry["public_id"] for entry in batch["expected"]]
        )
        batches.pop(nonce, None)
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse({"error": str(exc)}, status=400)
    except PermissionDenied:
        raise
    except Exception:
        logger.exception("Could not verify Cloudinary gallery upload batch %s.", nonce)
        _delete_gallery_assets(
            [entry["public_id"] for entry in batch["expected"]]
        )
        batches.pop(nonce, None)
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
        return JsonResponse(
            {"error": "Cloudinary could not verify the gallery images. Please retry."},
            status=502,
        )

    batch["verified_assets"] = verified_assets
    batch["finalized"] = True
    batches[nonce] = batch
    request.session[GALLERY_UPLOAD_SESSION_KEY] = batches
    return JsonResponse({"finalized": True, "count": len(verified_assets)})


def _build_gallery_groups(gallery_items):
    grouped_map = defaultdict(list)

    for item in gallery_items:
        customer = None
        if item.job_photo and item.job_photo.booking and item.job_photo.booking.customer:
            customer = item.job_photo.booking.customer
            key = f"customer-{customer.id}"
        else:
            key = f"item-{item.id}"

        grouped_map[key].append(item)

    gallery_groups = []
    for key, items in grouped_map.items():
        items = sorted(items, key=lambda x: x.created_at, reverse=True)
        first_item = items[0]
        customer = None
        if first_item.job_photo and first_item.job_photo.booking and first_item.job_photo.booking.customer:
            customer = first_item.job_photo.booking.customer

        preview_media = []
        for item in items:
            item_media = []
            for media in item.gallery_media or []:
                if media and media.get("is_image"):
                    item_media.append(media)
            if item_media:
                preview_media = item_media
                break

        gallery_groups.append(
            {
                "customer": customer,
                "items": items,
                "title": customer.gallery_display_name if customer else first_item.title,
                "service_type": first_item.service_type,
                "suburb": customer.suburb_postcode if customer and customer.suburb_postcode else first_item.suburb,
                "media": preview_media,
                "primary_media": preview_media[0] if preview_media else None,
            }
        )

    return gallery_groups


def gallery_page(request):
    """Display unified gallery with filtering options"""
    gallery_items = GalleryItem.objects.filter(featured=True).order_by("-created_at")

    # Get service type filter from query params
    service_filter = request.GET.get('service', '')
    if service_filter:
        gallery_items = gallery_items.filter(service_type=service_filter)

    # Get source filter from query params
    source_filter = request.GET.get('source', '')
    if source_filter:
        gallery_items = gallery_items.filter(source=source_filter)

    # Get unique service types for filter dropdown
    service_types = GalleryItem.objects.values_list('service_type', flat=True).distinct()
    source_types = GalleryItem.SOURCE_CHOICES
    gallery_groups = _build_gallery_groups(gallery_items)

    context = {
        "gallery_items": gallery_items,
        "gallery_groups": gallery_groups,
        "service_types": service_types,
        "source_types": source_types,
        "selected_service": service_filter,
        "selected_source": source_filter,
    }

    return render(request, "gallery/gallery.html", context)


@login_required
def delete_gallery_item_ajax(request, item_id):
    """Delete gallery item via AJAX (for public-facing deletion with auth)"""
    item = get_object_or_404(GalleryItem, id=item_id)

    if request.method == "POST":
        # Check if user is admin or staff
        if request.user.is_staff or request.user.is_superuser:
            item.delete()
            return JsonResponse({"success": True, "message": "Image deleted successfully"})
        return JsonResponse({"success": False, "message": "Permission denied"}, status=403)

    return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)