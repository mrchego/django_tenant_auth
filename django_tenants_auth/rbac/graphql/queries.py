import strawberry
from typing import List, Dict
from strawberry.types import Info

from django_tenants_auth.rbac.services import RBACService
from django_tenants_auth.rbac.graphql.types import (
    PermissionGroupEntryType, RoleType, PermissionGroupType, UserPermissionsType, UserRoleInfoType
)
from django_tenants_auth.tenants.models import Tenant


@strawberry.type
class RBACQuery:
    
    @strawberry.field
    def roles(self, info: Info) -> List[RoleType]:
        """Get all roles for current tenant."""
        tenant = info.context.request.tenant
        return tenant.roles.all()
    
    @strawberry.field
    def role(self, info: Info, id: strawberry.ID) -> RoleType:
        """Get a specific role."""
        tenant = info.context.request.tenant
        return tenant.roles.get(id=id)
    
    @strawberry.field
    def permissions_grouped(
        self,
        info: Info
    ) -> List[PermissionGroupEntryType]:
        """Get all permissions grouped by module."""

        grouped = RBACService.get_permissions_grouped()

        return [
            PermissionGroupEntryType(
                key=key,
                value=value,
            )
            for key, value in grouped.items()
    ]
    
    @strawberry.field
    def my_permissions(self, info: Info) -> UserPermissionsType:
        """Get current user's permissions in current tenant."""
        user = info.context.request.user
        tenant = info.context.request.tenant
        return RBACService.get_user_permissions(user, tenant)
    
    @strawberry.field
    def my_roles(self, info: Info) -> List[UserRoleInfoType]:
        """Get current user's roles in current tenant."""
        user = info.context.request.user
        tenant = info.context.request.tenant
        return RBACService.get_user_roles(user, tenant)
    
    @strawberry.field
    def user_permissions(
        self, 
        info: Info, 
        user_id: strawberry.ID
    ) -> UserPermissionsType:
        """Get a specific user's permissions in current tenant."""
        from django_tenants_auth.tenants.models import User
        tenant = info.context.request.tenant
        user = User.objects.get(id=user_id)
        return RBACService.get_user_permissions(user, tenant)