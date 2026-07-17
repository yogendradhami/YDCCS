from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
<<<<<<< HEAD
        import notifications.signals  # noqa: F401
=======
        import notifications.signals
>>>>>>> 5815f15 (Initial project commit)
