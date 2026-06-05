from django.db import models
from django_tenants.models import DomainMixin
from tenant_users.tenants.models import TenantBase, UserProfile
from django_tenants_auth.core.models import TimeStampedModel


class User(UserProfile):
    """
    Global user shared across tenants.
    """
    
    def __str__(self) -> str:
        return str(self.email)

class Tenant(TenantBase, TimeStampedModel):
    """
    Tenant/schema model.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["schema_name"]),  # keep this
        ]

    def __str__(self) -> str:
        return str(self.name)

class Domain(DomainMixin, TimeStampedModel):
    """
    Domain mapping for tenants.
    """

    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return str(self.domain)