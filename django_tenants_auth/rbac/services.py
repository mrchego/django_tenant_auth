from typing import List, Dict, Any, Optional, Set
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q

from django_tenants_auth.rbac.models import Role, UserRole, PermissionGroup
from django_tenants_auth.tenants.models import User, Tenant


class RBACService:
    """
    Service layer for all RBAC operations.
    
    This handles role creation, permission assignment, user-role mapping,
    and permission checking logic.
    """
    
    @staticmethod
    def create_role(
        *,
        name: str,
        tenant: Tenant,
        permissions: Optional[List[str]] = None,
        description: str = "",
        is_system_role: bool = False,
        created_by: Optional[User] = None,
    ) -> Role:
        """
        Create a new role with optional permissions.
        
        Args:
            name: Role name
            tenant: Tenant the role belongs to
            permissions: List of permission codenames (e.g., ['view_employee', 'add_employee'])
            description: Optional description
            is_system_role: Whether this is a system role (cannot be deleted)
            created_by: User creating the role
            
        Returns:
            Created Role instance
        """
        role = Role.objects.create(
            name=name,
            tenant=tenant,
            description=description,
            is_system_role=is_system_role,
            created_by=created_by,
        )
        
        if permissions:
            # Get Permission objects for the given codenames
            permission_objects = Permission.objects.filter(codename__in=permissions)
            role.permissions.set(permission_objects)
        
        return role
    
    @staticmethod
    def update_role(
        *,
        role: Role,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Role:
        """
        Update an existing role.
        
        Args:
            role: Role to update
            name: New name (optional)
            permissions: New list of permission codenames (optional)
            description: New description (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated Role instance
        """
        if name:
            role.name = name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active
        
        role.save()
        
        if permissions is not None:
            permission_objects = Permission.objects.filter(codename__in=permissions)
            role.permissions.set(permission_objects)
        
        return role
    
    @staticmethod
    def delete_role(role: Role) -> bool:
        """
        Delete a role if it's not a system role.
        
        Args:
            role: Role to delete
            
        Returns:
            True if deleted, False otherwise
            
        Raises:
            ValueError: If role is a system role
        """
        if role.is_system_role:
            raise ValueError(f"Cannot delete system role: {role.name}")
        
        role.delete()
        return True
    
    @staticmethod
    def assign_role_to_user(
        *,
        user: User,
        role: Role,
        assigned_by: Optional[User] = None,
    ) -> UserRole:
        """
        Assign a role to a user.
        
        Args:
            user: User to assign role to
            role: Role to assign
            assigned_by: User making the assignment
            
        Returns:
            Created UserRole instance
        """
        # Check if assignment already exists
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={
                'assigned_by': assigned_by,
                'is_active': True,
            }
        )
        
        if not created and not user_role.is_active:
            # Reactivate if previously deactivated
            user_role.is_active = True
            user_role.assigned_by = assigned_by
            user_role.save()
        
        return user_role
    
    @staticmethod
    def remove_role_from_user(
        *,
        user: User,
        role: Role,
    ) -> bool:
        """
        Remove a role from a user (deactivate the assignment).
        
        Args:
            user: User to remove role from
            role: Role to remove
            
        Returns:
            True if removed
        """
        try:
            user_role = UserRole.objects.get(user=user, role=role)
            user_role.is_active = False
            user_role.save()
            return True
        except UserRole.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_permissions(
        user: User,
        tenant: Tenant,
    ) -> Dict[str, Any]:
        """
        Get all permissions for a user in a specific tenant.
        
        This combines permissions from all active roles assigned to the user.
        
        Args:
            user: User to check
            tenant: Tenant context
            
        Returns:
            Dict with roles, permissions, and detailed breakdown
        """
        # Get all active user roles
        user_roles = UserRole.objects.filter(
            user=user,
            role__tenant=tenant,
            is_active=True,
            role__is_active=True,
        ).select_related('role')
        
        # Collect all permissions from all roles
        all_permissions: Set[str] = set()
        role_slugs = []
        
        for user_role in user_roles:
            role_slugs.append(user_role.role.slug)
            for perm in user_role.role.permissions.all():
                permission_string = f"{perm.content_type.app_label}.{perm.codename}"
                all_permissions.add(permission_string)
        
        return {
            "user_id": str(user.id),
            "tenant_slug": tenant.slug,
            "roles": role_slugs,
            "permissions": sorted(list(all_permissions)),
            "total_permissions": len(all_permissions),
        }
    
    @staticmethod
    def get_user_roles(
        user: User,
        tenant: Tenant,
    ) -> List[Dict[str, Any]]:
        """
        Get all active roles for a user in a tenant.
        
        Args:
            user: User to get roles for
            tenant: Tenant context
            
        Returns:
            List of role information dicts
        """
        user_roles = UserRole.objects.filter(
            user=user,
            is_active=True,
            role__tenant=tenant,
            role__is_active=True,
        ).select_related('role', 'assigned_by')
        
        return [
            {
                "id": str(ur.id),
                "role_id": str(ur.role.id),
                "role_name": ur.role.name,
                "role_slug": ur.role.slug,
                "description": ur.role.description,
                "is_system_role": ur.role.is_system_role,
                "assigned_by": ur.assigned_by.email if ur.assigned_by else None,
                "assigned_at": ur.created_at.isoformat(),
                "is_active": ur.is_active,
            }
            for ur in user_roles
        ]
    
    @staticmethod
    def user_has_permission(
        user: User,
        tenant: Tenant,
        permission_string: str,
    ) -> bool:
        """
        Check if a user has a specific permission in a tenant.
        
        Args:
            user: User to check
            tenant: Tenant context
            permission_string: Permission in format 'app_label.codename'
                              e.g., 'employees.view_employee'
            
        Returns:
            True if user has the permission
        """
        # Parse permission string
        try:
            app_label, codename = permission_string.split('.')
        except ValueError:
            return False
        
        # Check if any of user's roles have this permission
        has_perm = UserRole.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True,
            role__tenant=tenant,
            role__permissions__codename=codename,
            role__permissions__content_type__app_label=app_label,
        ).exists()
        
        return has_perm
    
    @staticmethod
    def get_permissions_grouped() -> Dict[str, Any]:
        """
        Get all permissions grouped by their permission groups.
        
        This is used for the frontend role creation UI.
        
        Returns:
            Dict of permission groups with their permissions
        """
        groups = PermissionGroup.objects.prefetch_related(
            'permissions__content_type'
        ).order_by('order')
        
        result = {}
        for group in groups:
            result[group.slug] = {
                "id": str(group.id),
                "name": group.name,
                "slug": group.slug,
                "description": group.description,
                "order": group.order,
                "permissions": [
                    {
                        "id": str(perm.id),
                        "name": perm.name,
                        "codename": perm.codename,
                        "slug": f"{perm.content_type.app_label}.{perm.codename}",
                        "app_label": perm.content_type.app_label,
                    }
                    for perm in group.permissions.all().order_by('codename')
                ],
            }
        
        return result
    
    @staticmethod
    def seed_default_roles(tenant: Tenant) -> Dict[str, Role]:
        """
        Seed default roles for a new tenant.
        
        This creates the standard role hierarchy:
        - Owner: Full access
        - Admin: Administrative access
        - HR Manager: HR management
        - Accountant: Financial management
        - Supervisor: Team supervision
        - Employee: Basic access
        
        Args:
            tenant: Tenant to seed roles for
            
        Returns:
            Dict mapping role slugs to Role instances
        """
        # Define default roles
        default_roles_config = {
            "owner": {
                "name": "Owner",
                "description": "Full system access with all permissions",
                "is_system_role": True,
            },
            "admin": {
                "name": "Admin",
                "description": "Administrative access to manage system",
                "is_system_role": True,
            },
            "hr_manager": {
                "name": "HR Manager",
                "description": "Human resources management access",
                "is_system_role": False,
            },
            "accountant": {
                "name": "Accountant",
                "description": "Financial and accounting access",
                "is_system_role": False,
            },
            "supervisor": {
                "name": "Supervisor",
                "description": "Team supervision and management access",
                "is_system_role": False,
            },
            "employee": {
                "name": "Employee",
                "description": "Basic employee self-service access",
                "is_system_role": False,
            },
        }
        
        created_roles = {}
        
        for slug, config in default_roles_config.items():
            role, created = Role.objects.get_or_create(
                tenant=tenant,
                slug=slug,
                defaults={
                    "name": config["name"],
                    "description": config["description"],
                    "is_system_role": config["is_system_role"],
                }
            )
            created_roles[slug] = role
        
        # Assign all permissions to Owner role
        owner_role = created_roles["owner"]
        all_permissions = Permission.objects.all()
        owner_role.permissions.set(all_permissions)
        
        # Assign basic permissions to Employee role
        employee_role = created_roles["employee"]
        basic_permissions = Permission.objects.filter(
            codename__startswith='view_'
        )
        employee_role.permissions.set(basic_permissions)
        
        return created_roles


class PermissionSeeder:
    """
    Handles seeding of permissions and permission groups.
    
    This is typically called during initial setup or when adding new modules.
    """
    
    # Define the permission structure
    PERMISSION_GROUPS_CONFIG = {
        "employee_management": {
            "name": "Employee Management",
            "description": "Permissions for managing employee records",
            "order": 1,
            "permissions": [
                ("view_employee", "Can view employees"),
                ("add_employee", "Can add employees"),
                ("change_employee", "Can change employees"),
                ("delete_employee", "Can delete employees"),
            ],
        },
        "department_management": {
            "name": "Department Management",
            "description": "Permissions for managing departments",
            "order": 2,
            "permissions": [
                ("view_department", "Can view departments"),
                ("add_department", "Can add departments"),
                ("change_department", "Can change departments"),
                ("delete_department", "Can delete departments"),
            ],
        },
        "role_management": {
            "name": "Role Management",
            "description": "Permissions for managing roles and permissions",
            "order": 3,
            "permissions": [
                ("view_role", "Can view roles"),
                ("add_role", "Can add roles"),
                ("change_role", "Can change roles"),
                ("delete_role", "Can delete roles"),
                ("manage_roles", "Can manage roles and permissions"),
            ],
        },
        "user_management": {
            "name": "User Management",
            "description": "Permissions for managing users and access",
            "order": 4,
            "permissions": [
                ("view_user", "Can view users"),
                ("add_user", "Can add users"),
                ("change_user", "Can change users"),
                ("delete_user", "Can delete users"),
            ],
        },
        "payroll": {
            "name": "Payroll Management",
            "description": "Permissions for payroll processing",
            "order": 5,
            "permissions": [
                ("view_payroll", "Can view payroll"),
                ("process_payroll", "Can process payroll"),
                ("approve_payroll", "Can approve payroll"),
            ],
        },
        "reports": {
            "name": "Reports & Analytics",
            "description": "Permissions for viewing and exporting reports",
            "order": 6,
            "permissions": [
                ("view_reports", "Can view reports"),
                ("export_reports", "Can export reports"),
                ("create_reports", "Can create custom reports"),
            ],
        },
        "settings": {
            "name": "System Settings",
            "description": "Permissions for system configuration",
            "order": 7,
            "permissions": [
                ("view_settings", "Can view settings"),
                ("change_settings", "Can change settings"),
                ("manage_tenant", "Can manage tenant settings"),
            ],
        },
    }
    
    @staticmethod
    def seed_permissions_and_groups():
        """
        Seed all permissions and permission groups.
        
        This creates the permission structure in the database.
        It can be called multiple times safely - it will update existing records.
        """
        # Get or create a content type for our custom permissions
        content_type, created = ContentType.objects.get_or_create(
            app_label='rbac',
            model='custompermission'
        )
        
        created_count = 0
        updated_count = 0
        
        for group_slug, group_config in PermissionSeeder.PERMISSION_GROUPS_CONFIG.items():
            # Create or update permission group
            group, group_created = PermissionGroup.objects.update_or_create(
                slug=group_slug,
                defaults={
                    "name": group_config["name"],
                    "description": group_config["description"],
                    "order": group_config["order"],
                }
            )
            
            if group_created:
                created_count += 1
            else:
                updated_count += 1
            
            # Create permissions for this group
            permissions = []
            for codename, name in group_config["permissions"]:
                perm, perm_created = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={"name": name}
                )
                permissions.append(perm)
            
            # Associate permissions with group
            group.permissions.set(permissions)
        
        return {
            "groups_created": created_count,
            "groups_updated": updated_count,
            "total_groups": len(PermissionSeeder.PERMISSION_GROUPS_CONFIG),
        }