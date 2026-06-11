import strawberry
from typing import List, Optional
from strawberry_django import DjangoModelType

from django_tenants_auth.rbac import models


@strawberry.django.type(models.Role)
class RoleType:
    id: strawberry.ID
    name: str
    slug: str
    description: str
    is_system_role: bool
    created_at: str
    permissions: List['PermissionType']


@strawberry.django.type(models.UserRole)
class UserRoleType:
    id: strawberry.ID
    user_id: strawberry.ID
    role: RoleType
    assigned_by_id: Optional[strawberry.ID]
    is_active: bool
    created_at: str


@strawberry.type
class PermissionType:
    id: strawberry.ID
    name: str
    codename: str
    slug: str


@strawberry.type
class PermissionGroupType:
    name: str
    slug: str
    permissions: List[PermissionType]


@strawberry.type
class UserPermissionsType:
    roles: List[str]
    permissions: List[str]
    role_permissions: List[str]
    direct_permissions: List[str]


@strawberry.type
class UserRoleInfoType:
    id: strawberry.ID

    role_id: strawberry.ID

    role_name: str

    role_slug: str

    description: Optional[str]

    is_system_role: bool

    assigned_by: Optional[str]

    assigned_at: str

    is_active: bool
    
@strawberry.type
class PermissionGroupEntryType:
    key: str
    value: PermissionGroupType