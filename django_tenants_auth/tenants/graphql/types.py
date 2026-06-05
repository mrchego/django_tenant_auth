import strawberry
from strawberry import auto
from strawberry_django.type import type
from django_tenants_auth.tenants.models import User, Tenant

@type(User)
class UserType:
    id: auto
    email: auto
    is_verified: auto


@type(Tenant)
class TenantType:
    id: auto
    name: auto
    slug: auto
    schema_name: auto