from django.urls import path
<<<<<<< HEAD

from .views import gallery_page

urlpatterns = [
    path("gallery/", gallery_page, name="gallery"),
]
=======
from .views import gallery_page


urlpatterns = [
    path("gallery/", gallery_page, name="gallery"),
]
>>>>>>> 5815f15 (Initial project commit)
