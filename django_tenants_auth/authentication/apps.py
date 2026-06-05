from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_tenants_auth.authentication"
    label = "authentication"
    verbose_name = "Authentication & Authorization"

    def ready(self):
        # Import signals if needed in the future
        pass