from typing import Optional

import strawberry
from strawberry.types import Info
from django_tenants_auth.authentication.decorators import login_required

from django_tenants_auth.authentication.services import AuthenticationService
from django_tenants_auth.authentication.graphql.types import (
    CurrentUserResponseType,
    UserType,
)
from django_tenants_auth.tenants.models import Tenant

@strawberry.type
class AuthQuery:
    
    @strawberry.field
    @login_required
    def me(
        self,
        info: Info,
        tenant_slug: Optional[str] = None,
    ) -> CurrentUserResponseType:
        """
        Get current authenticated user's full information.
        
        If `tenantSlug` is provided, it will override the current tenant
        (the user must be a member of that tenant).
        """
        user = info.context.request.user
        
        if tenant_slug:
            # Use the explicitly provided tenant
            tenant = user.tenants.get(slug=tenant_slug)
        else:
            tenant = info.context.request.tenant
        
        return AuthenticationService.get_current_user_info(user, tenant)
    
    @strawberry.field
    @login_required
    def current_user(self, info: Info) -> UserType:
        """Get basic current user information."""
        user = info.context.request.user
        return UserType(
            id=str(user.id),
            email=user.email,
            is_verified=user.is_verified,
            is_active=user.is_active,
        )
    
    @strawberry.field
    def hello(self) -> str:
        """Simple health check query."""
        return "Hello from multi-tenant SaaS authentication!"