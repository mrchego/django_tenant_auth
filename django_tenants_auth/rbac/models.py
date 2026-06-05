from django.db import models
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify

from django_tenants_auth.core.models import TimeStampedModel


class Role(TimeStampedModel):
    """
    Tenant-scoped role that groups permissions together.
    
    Roles are created within each tenant schema and can be assigned to users.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='roles',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True, default="")
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='rbac_roles'
    )
    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles (Owner, Admin) cannot be deleted"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'tenants.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_roles'
    )

    class Meta:
        unique_together = [('tenant', 'slug')]
        ordering = ['name']
        permissions = [
            ("manage_roles", "Can manage roles and permissions"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_permission_codenames(self):
        """Get list of permission codenames for this role."""
        return list(self.permissions.values_list('codename', flat=True))


class UserRole(TimeStampedModel):
    """
    Maps users to roles within a tenant.
    
    A user can have multiple roles, and each role assignment is tracked.
    """
    user = models.ForeignKey(
        'tenants.User',
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    assigned_by = models.ForeignKey(
        'tenants.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles'
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'role']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


class PermissionGroup(TimeStampedModel):
    """
    Groups permissions by module for frontend organization.
    
    This helps display permissions in a clean, grouped UI.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='permission_groups'
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Permission Group"
        verbose_name_plural = "Permission Groups"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)