from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_tenants_auth.tenants"
    label = "tenants"

    def ready(self):
        from . import signals