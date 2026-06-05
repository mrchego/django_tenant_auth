from django.apps import AppConfig


class RBACConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_tenants_auth.rbac"
    label = "rbac"
    verbose_name = "Role Based Access Control"

    def ready(self):
        # Import signals if needed
        pass