from django.apps import AppConfig


class MorseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "morse"
    verbose_name = "Morse"

    def ready(self):
        import morse.admin  # noqa: F401 — register ModelAdmins
        import morse.signals  # noqa: F401
