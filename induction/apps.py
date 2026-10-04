from django.apps import AppConfig


class InductionConfig(AppConfig):

    default_auto_field = (
        "django.db.models.BigAutoField"
    )

    name = "induction"

    verbose_name = (
        "Employee Induction & Onboarding"
    )

    def ready(self):

        import induction.signals