import strawberry
from typing import List, Optional
from strawberry.types import Info

from django_tenants_auth.rbac.services import RBACService
from django_tenants_auth.rbac.graphql.types import RoleType, UserRoleType
from django_tenants_auth.rbac.models import Role


@strawberry.type
class RBACMutation:
    
    @strawberry.mutation
    def create_role(
        self,
        info: Info,
        name: str,
        permissions: List[str],
        description: str = "",
    ) -> RoleType:
        """Create a new role with permissions."""
        tenant = info.context.request.tenant
        user = info.context.request.user
        
        role = RBACService.create_role(
            name=name,
            tenant=tenant,
            permissions=permissions,
            description=description,
            created_by=user,
        )
        return role
    
    @strawberry.mutation
    def update_role(
        self,
        info: Info,
        role_id: strawberry.ID,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> RoleType:
        """Update an existing role."""
        tenant = info.context.request.tenant
        role = Role.objects.get(id=role_id, tenant=tenant)
        
        if name:
            role.name = name
        if description is not None:
            role.description = description
        if permissions is not None:
            from django.contrib.auth.models import Permission
            perms = Permission.objects.filter(codename__in=permissions)
            role.permissions.set(perms)
        
        role.save()
        return role
    
    @strawberry.mutation
    def delete_role(
        self,
        info: Info,
        role_id: strawberry.ID,
    ) -> bool:
        """Delete a role."""
        tenant = info.context.request.tenant
        role = Role.objects.get(id=role_id, tenant=tenant)
        
        if role.is_system_role:
            raise Exception("Cannot delete system roles")
        
        role.delete()
        return True
    
    @strawberry.mutation
    def assign_role(
        self,
        info: Info,
        user_id: strawberry.ID,
        role_id: strawberry.ID,
    ) -> UserRoleType:
        """Assign a role to a user."""
        from django_tenants_auth.tenants.models import User
        
        tenant = info.context.request.tenant
        assigner = info.context.request.user
        user = User.objects.get(id=user_id)
        role = Role.objects.get(id=role_id, tenant=tenant)
        
        user_role = RBACService.assign_role_to_user(
            user=user,
            role=role,
            tenant=tenant,
            assigned_by=assigner,
        )
        return user_role
    
    @strawberry.mutation
    def remove_role(
        self,
        info: Info,
        user_role_id: strawberry.ID,
    ) -> bool:
        """Remove a role from a user."""
        from django_tenants_auth.rbac.models import UserRole
        
        tenant = info.context.request.tenant
        user_role = UserRole.objects.get(
            id=user_role_id,
            role__tenant=tenant
        )
        user_role.delete()
        return True