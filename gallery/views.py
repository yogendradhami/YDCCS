<<<<<<< HEAD
# Create your views here.
from django.shortcuts import render

=======
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
>>>>>>> 5815f15 (Initial project commit)
from .models import GalleryItem


def gallery_page(request):
    gallery_items = GalleryItem.objects.all().order_by("-created_at")

<<<<<<< HEAD
    return render(request, "gallery.html", {"gallery_items": gallery_items})
=======
    return render(
        request,
        "gallery/gallery.html",
        {
            "gallery_items": gallery_items
        }
    )
>>>>>>> 5815f15 (Initial project commit)
