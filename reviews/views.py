from django.shortcuts import render

from .models import Review


def reviews_page(request):
    reviews = Review.objects.filter(featured=True).order_by("-created_at")[:6]
    # reviews = Review.objects.all().order_by("-created_at")

    return render(request, "reviews.html", {"reviews": reviews})
