import strawberry
from typing import List, Optional

from django_tenants_auth.rbac.graphql.types import UserRoleInfoType


@strawberry.type
class VerificationResponseType:
    status: str
    message: str
    user_id: Optional[strawberry.ID] = None
    email: Optional[str] = None
    email_sent: Optional[bool] = None
    company_name: Optional[str] = None
    subdomain: Optional[str] = None


@strawberry.type
class RegistrationCompleteType:
    """Response for completed registration."""
    status: str
    message: str
    user: Optional['UserType'] = None
    tenant: Optional['TenantType'] = None
    domain: Optional[str] = None
    tokens: Optional['AuthTokensType'] = None


@strawberry.type
class PasswordResetInitiateType:
    """Response for password reset initiation."""
    status: str
    message: str


@strawberry.type
class PasswordResetCompleteType:
    """Response for completed password reset."""
    status: str
    message: str


# ... rest of existing types ...
@strawberry.type
class UserType:
    id: strawberry.ID
    email: str
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    last_login: Optional[str] = None


@strawberry.type
class TenantType:
    id: strawberry.ID
    name: str
    slug: str
    schema_name: str


@strawberry.type
class AvailableTenantType:
    id: strawberry.ID
    name: str
    slug: str
    schema_name: str
    roles: List[str]
    is_current: bool


@strawberry.type
class AuthTokensType:
    access_token: str
    refresh_token: str


@strawberry.type
class LoginResponseType:
    user: UserType
    current_tenant: TenantType
    available_tenants: List[AvailableTenantType]
    roles: List[UserRoleInfoType]
    permissions: List[str]
    tokens: AuthTokensType


@strawberry.type
class RegistrationResponseType:
    user: UserType
    tenant: TenantType
    domain: str
    tokens: AuthTokensType


@strawberry.type
class TenantSwitchResponseType:
    tenant: TenantType
    roles: List[UserRoleInfoType]
    permissions: List[str]


@strawberry.type
class CurrentUserResponseType:
    user: UserType
    current_tenant: TenantType
    available_tenants: List[AvailableTenantType]
    roles: List[UserRoleInfoType]
    permissions: List[str]


@strawberry.type
class LogoutResponseType:
    success: bool
    message: str