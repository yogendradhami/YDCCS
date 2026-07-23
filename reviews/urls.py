from django.urls import path

from .views import reviews_page

urlpatterns = [
    path("reviews/", reviews_page, name="reviews"),
]
