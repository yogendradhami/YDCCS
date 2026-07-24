# Create your views here.
from collections import defaultdict
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import GalleryItem


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

        gallery_groups.append(
            {
                "customer": customer,
                "items": items,
                "title": customer.gallery_display_name if customer else first_item.title,
                "service_type": first_item.service_type,
                "suburb": customer.suburb_postcode if customer and customer.suburb_postcode else first_item.suburb,
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

