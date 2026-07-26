from django.apps import AppConfig


class GalleryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gallery"

    def ready(self):
        from pillow_heif import register_heif_opener
        register_heif_opener()

        import gallery.signals