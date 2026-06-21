# Create your views here.
from django.shortcuts import render

from .models import GalleryItem


def gallery_page(request):
    gallery_items = GalleryItem.objects.all().order_by("-created_at")

    return render(request, "gallery.html", {"gallery_items": gallery_items})
