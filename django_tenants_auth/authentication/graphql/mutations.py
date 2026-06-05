import strawberry
from typing import Optional
from strawberry.types import Info
from django_tenants_auth.authentication.decorators import login_required

from django_tenants_auth.authentication.services import (
    AuthenticationService,
    AuthenticationError,
)
from django_tenants_auth.authentication.graphql.types import (
    AvailableTenantType,
    LoginResponseType,
    RegistrationResponseType,
    TenantSwitchResponseType,
    AuthTokensType,
    LogoutResponseType,
    TenantType,
    UserType,
    VerificationResponseType,
    RegistrationCompleteType,
)
from django_tenants_auth.rbac.graphql.types import UserRoleInfoType


@strawberry.type
class AuthMutation:
    
    @strawberry.mutation
    def login(
        self,
        info: Info,
        email: str,
        password: str,
        tenant_slug: Optional[str] = None,
    ) -> LoginResponseType:
        try:
            request = info.context.request
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            data = AuthenticationService.login_user(
                email=email,
                password=password,
                tenant_slug=tenant_slug,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Build Strawberry types from dict
            user = UserType(**data['user'])
            current_tenant = TenantType(**data['current_tenant'])
            tokens = AuthTokensType(**data['tokens'])

            available_tenants = [
                AvailableTenantType(
                    id=t['id'],
                    name=t['name'],
                    slug=t['slug'],
                    schema_name=t['schema_name'],
                    roles=t['roles'],
                    is_current=t['is_current'],
                ) for t in data['available_tenants']
            ]

            roles = [
                UserRoleInfoType(**r) for r in data['roles']
            ]

            return LoginResponseType(
                user=user,
                current_tenant=current_tenant,
                available_tenants=available_tenants,
                roles=roles,
                permissions=data['permissions'],
                tokens=tokens,
            )

        except AuthenticationError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    @strawberry.mutation
    @login_required
    def switch_tenant(
        self,
        info: Info,
        tenant_slug: str,
    ) -> TenantSwitchResponseType:
        """
        Switch to a different tenant.
        
        The user must be a member of the target tenant.
        Returns updated roles and permissions for the new tenant.
        """
        try:
            user = info.context.request.user
            return AuthenticationService.switch_tenant(user, tenant_slug)
        except AuthenticationError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Tenant switch failed: {str(e)}")
    
    @strawberry.mutation
    def refresh_token(
        self,
        info: Info,
        refresh_token: str,
    ) -> AuthTokensType:
        """
        Refresh an expired access token using a refresh token.
        
        Returns new access and refresh token pair.
        The old refresh token is invalidated (token rotation).
        """
        try:
            return AuthenticationService.refresh_token(refresh_token)
        except AuthenticationError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Token refresh failed: {str(e)}")
    
    @strawberry.mutation
    @login_required
    def logout(
        self,
        info: Info,
        refresh_token: Optional[str] = None,
    ) -> LogoutResponseType:
        """
        Logout user by revoking refresh token(s).
        
        If refresh_token is provided, only that token is revoked.
        Otherwise, all refresh tokens for the user are revoked.
        """
        try:
            user = info.context.request.user
            success = AuthenticationService.logout_user(user, refresh_token)
            
            return LogoutResponseType(
                success=success,
                message="Logged out successfully" if success else "Logout failed"
            )
        except Exception as e:
            return LogoutResponseType(
                success=False,
                message=f"Logout failed: {str(e)}"
            )
            
    @strawberry.mutation
    def initiate_registration(
        self,
        info: Info,
        email: str,
        password: str,
        company_name: str,
        subdomain: str,
    ) -> VerificationResponseType:
        """
        Step 1: Start registration and send verification email.
        """
        try:
            data = AuthenticationService.initiate_registration(
                email=email,
                password=password,
                company_name=company_name,
                subdomain=subdomain,
            )
            return VerificationResponseType(
                status=data["status"],
                message=data["message"],
                user_id=data.get("user_id"),
                email=data.get("email"),
                email_sent=data.get("email_sent", False),
            )
        except AuthenticationError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Registration initiation failed: {str(e)}")

    @strawberry.mutation
    def verify_email_and_complete_registration(
        self,
        info: Info,
        user_id: strawberry.ID,
        code: str,
    ) -> RegistrationCompleteType:
        """
        Step 2: Verify email code and finalise tenant creation.
        """
        try:
            data = AuthenticationService.verify_email_and_complete_registration(
                user_id=str(user_id),
                code=code,
            )
            return RegistrationCompleteType(
                status=data["status"],
                message=data["message"],
                user=UserType(**data["user"]),
                tenant=TenantType(**data["tenant"]),
                domain=data["domain"],
                tokens=AuthTokensType(**data["tokens"]),
            )
        except AuthenticationError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Verification failed: {str(e)}")