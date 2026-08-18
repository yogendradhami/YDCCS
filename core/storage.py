import cloudinary
import cloudinary.uploader

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryVideoStorage(Storage):
    """
    Storage backend specifically for testimonial videos.

    Uploads MP4/video files to Cloudinary as video resources.
    """

    def _save(self, name, content):
        result = cloudinary.uploader.upload(
            content,
            resource_type="video",
            folder="testimonial-videos",
        )

        return result["public_id"]

    def url(self, name):
        return cloudinary.utils.cloudinary_url(
            name,
            resource_type="video",
            secure=True,
        )[0]

    def exists(self, name):
        return False

    def delete(self, name):
        if name:
            cloudinary.uploader.destroy(
                name,
                resource_type="video",
            )