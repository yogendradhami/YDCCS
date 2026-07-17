from django.urls import path
<<<<<<< HEAD

from .views import reviews_page

urlpatterns = [
    path("reviews/", reviews_page, name="reviews"),
]
=======
from .views import reviews_page


urlpatterns = [
    path("reviews/", reviews_page, name="reviews"),
]
>>>>>>> 5815f15 (Initial project commit)
