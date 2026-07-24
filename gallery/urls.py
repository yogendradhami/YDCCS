from django.urls import path

from .views import gallery_page, delete_gallery_item_ajax

urlpatterns = [
    path("gallery/", gallery_page, name="gallery"),
    path("gallery/<int:item_id>/delete/", delete_gallery_item_ajax, name="delete_gallery_item_ajax"),
]
