from django.shortcuts import render
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import Review


def reviews_page(request):
<<<<<<< HEAD
    reviews = Review.objects.filter(featured=True).order_by("-created_at")[:6]
    # reviews = Review.objects.all().order_by("-created_at")

    return render(request, "reviews.html", {"reviews": reviews})
=======
    reviews = Review.objects.filter( featured=True ).order_by("-created_at")[:6]
    # reviews = Review.objects.all().order_by("-created_at")

    return render(
        request,
        "reviews/reviews.html",
        {
            "reviews": reviews
        }
    )
>>>>>>> 5815f15 (Initial project commit)
