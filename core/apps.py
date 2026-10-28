from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .media_cleanup import connect_cloudinary_cleanup_signals

        connect_cloudinary_cleanup_signals()
