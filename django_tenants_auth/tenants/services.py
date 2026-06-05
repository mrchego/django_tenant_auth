from tenant_users.tenants.tasks import provision_tenant

from django_tenants_auth.tenants.models import Tenant, User


def create_tenant_service(
    *,
    name: str,
    slug: str,
    owner: User,
) -> Tenant:

    tenant, domain = provision_tenant(
        tenant_name=name,
        tenant_slug=slug,
        schema_name=slug,
        owner=owner,
        is_superuser=True,
        is_staff=True,
    )

    return tenant