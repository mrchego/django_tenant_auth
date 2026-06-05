from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_tenants_auth.employees"
    label = "employees"
    verbose_name = "Employee Management"

    def ready(self):
        # Import signals if needed
        pass