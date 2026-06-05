import strawberry
from strawberry.types import Info
from django_tenants_auth.authentication.decorators import login_required

from django_tenants_auth.authentication.services import AuthenticationService
from django_tenants_auth.authentication.graphql.types import (
    CurrentUserResponseType,
    UserType,
)


@strawberry.type
class AuthQuery:
    
    @strawberry.field
    @login_required
    def me(self, info: Info) -> CurrentUserResponseType:
        """
        Get current authenticated user's full information.
        
        This includes:
        - User details
        - Current tenant
        - Available tenants
        - Roles in current tenant
        - Permissions in current tenant
        """
        user = info.context.request.user
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