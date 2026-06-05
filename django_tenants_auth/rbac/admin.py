from django.contrib import admin
from django_tenants_auth.core.admin import TimeStampedModelAdmin
from django_tenants_auth.rbac.models import Role, UserRole, PermissionGroup


@admin.register(Role)
class RoleAdmin(TimeStampedModelAdmin):
    list_display = ['name', 'slug', 'is_system_role', 'is_active', 'created_at']
    list_filter = ['is_system_role', 'is_active']
    search_fields = ['name', 'slug']
    filter_horizontal = ['permissions']
    readonly_fields = TimeStampedModelAdmin.readonly_fields + ['slug']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_system_role', 'is_active')
        }),
        ('Permissions', {
            'fields': ('permissions',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(UserRole)
class UserRoleAdmin(TimeStampedModelAdmin):
    list_display = ['user', 'role', 'is_active', 'assigned_by', 'created_at']
    list_filter = ['is_active', 'role']
    search_fields = ['user__email', 'role__name']
    readonly_fields = TimeStampedModelAdmin.readonly_fields


@admin.register(PermissionGroup)
class PermissionGroupAdmin(TimeStampedModelAdmin):
    list_display = ['name', 'slug', 'order', 'created_at']
    list_filter = ['order']
    search_fields = ['name', 'slug']
    filter_horizontal = ['permissions']
    readonly_fields = TimeStampedModelAdmin.readonly_fields + ['slug']