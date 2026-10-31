from django.apps import AppConfig


class QuotesConfig(AppConfig):
    name = "quotes"

    def ready(self):
        from . import signals
