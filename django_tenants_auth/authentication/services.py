import jwt
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from django_tenants.utils import schema_context
from django.db import transaction

from django_tenants_auth.tenants.models import User, Tenant
from django_tenants_auth.rbac.services import RBACService, PermissionSeeder
from django_tenants_auth.authentication.models import (
    RefreshToken as RefreshTokenModel,
    LoginAttempt,
    EmailVerificationToken,
    PasswordResetToken,
)
from django_tenants_auth.authentication.email_service import EmailService
import logging
logger = logging.getLogger(__name__)
from django.db import transaction as db_transaction
from django.core.management import call_command
from django.db import connection
class AuthenticationService:
    """Service layer for authentication operations."""
    
    @staticmethod
    def generate_jwt_tokens(user: User, device_info: Optional[Dict] = None) -> Dict[str, str]:
        """Generate JWT access and refresh tokens."""
        token_id = str(uuid.uuid4())
        
        access_token = jwt.encode(
            {
                "user_id": str(user.id),
                "email": user.email,
                "token_id": token_id,
                "exp": datetime.utcnow() + timedelta(hours=1),
                "type": "access",
                "iat": datetime.utcnow(),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        
        refresh_token = jwt.encode(
            {
                "user_id": str(user.id),
                "token_id": token_id,
                "exp": datetime.utcnow() + timedelta(days=30),
                "type": "refresh",
                "iat": datetime.utcnow(),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        
        expires_at = timezone.now() + timedelta(days=30)
        RefreshTokenModel.objects.create(
            user=user,
            token=hashlib.sha256(refresh_token.encode()).hexdigest(),
            is_valid=True,
            expires_at=expires_at,
            device_info=device_info or {},
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    
    @staticmethod
    def initiate_registration(
        *,
        email: str,
        password: str,
        company_name: str,
        subdomain: str,
    ) -> Dict[str, Any]:
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            existing_user = User.objects.get(email=email)
            if existing_user.is_verified:
                raise AuthenticationError(
                    "An account with this email already exists. Please login instead.",
                    code="EMAIL_EXISTS"
                )
            else:
                # User exists but not verified - resend verification
                AuthenticationService._send_verification_email(existing_user, 'registration')
                return {
                    "status": "pending_verification",
                    "message": "Verification code resent to your email.",
                    "user_id": str(existing_user.id),
                    "email": email,
                }
        
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                is_active=False,
            )
            user.is_verified = False
            user.save(update_fields=['is_verified'])

            # No registration_data stored on user

            success = AuthenticationService._send_verification_email(user, 'registration')
            
            return {
                "status": "pending_verification",
                "message": "Verification code sent to your email.",
                "user_id": str(user.id),
                "email": email,
                "email_sent": success,
                # Return the registration info so frontend can hold it
                "company_name": company_name,
                "subdomain": subdomain,
            }
            
    
    @staticmethod
    def _send_verification_email(user: User, purpose: str) -> bool:
        """
        Create verification token and send email.
        """
        # Invalidate old verification tokens
        EmailVerificationToken.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True)
        
        # Generate new code
        code = EmailVerificationToken.generate_code()
        
        # Create token (valid for 15 minutes)
        EmailVerificationToken.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        
        # Send email
        return EmailService.send_email_verification(user, code)
    
    @staticmethod
    def verify_email_and_complete_registration(
        *,
        user_id: str,
        code: str,
        company_name: str,   # new parameter
        subdomain: str,      # new parameter
    ) -> Dict[str, Any]:
        """
        Step 2: Verify email and complete registration.
        
        This will:
        1. Verify the code
        2. Mark user as verified and active
        3. Create the tenant
        4. Set up roles and permissions
        5. Return auth tokens
        """
        from tenant_users.tenants.tasks import provision_tenant
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationError("User not found", code="USER_NOT_FOUND")
        
        # Get verification token
        try:
            verification = EmailVerificationToken.objects.get(
                user=user,
                code=code,
                purpose='registration',
                is_used=False,
            )
        except EmailVerificationToken.DoesNotExist:
            raise AuthenticationError(
                "Invalid verification code. Please request a new one.",
                code="INVALID_CODE"
            )
        
        # Check if token is valid
        if not verification.is_valid():
            if verification.expires_at <= timezone.now():
                raise AuthenticationError(
                    "Verification code has expired. Please request a new one.",
                    code="CODE_EXPIRED"
                )
            elif verification.attempts >= verification.max_attempts:
                raise AuthenticationError(
                    "Too many attempts. Please request a new verification code.",
                    code="MAX_ATTEMPTS"
                )
        
        # Mark token as used
        verification.mark_as_used()
        
        with transaction.atomic():
            # Activate user
            user.is_verified = True
            user.is_active = True
            user.save()
            
            # Create tenant
            tenant, domain = provision_tenant(
                tenant_name=company_name,
                tenant_slug=subdomain,
                schema_name=subdomain,
                owner=user,
                is_superuser=True,
                is_staff=True,
            )
            
            # Force creation of employees tables (idempotent)
            with schema_context(subdomain):
                from django.db import connection
                from django.apps import apps

                Employee = apps.get_model('employees', 'Employee')
                Department = apps.get_model('employees', 'Department')

                # Check if tables exist before trying to create
                with connection.cursor() as cursor:
                    cursor.execute("SELECT to_regclass('employees_department');")
                    dept_exists = cursor.fetchone()[0] is not None
                    cursor.execute("SELECT to_regclass('employees_employee');")
                    emp_exists = cursor.fetchone()[0] is not None

                if not dept_exists or not emp_exists:
                    try:
                        with transaction.atomic():   # <--- savepoint
                            with connection.schema_editor() as schema_editor:
                                if not dept_exists:
                                    schema_editor.create_model(Department)
                                if not emp_exists:
                                    schema_editor.create_model(Employee)
                    except Exception as e:
                        # Savepoint rolls back, outer transaction continues
                        logger.error(f"Error creating employee tables: {e}")

                # Ensure migration record is set (ignore if already exists)
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO django_migrations (app, name, applied) "
                            "VALUES ('employees', '0001_initial', NOW())"
                        )
                except Exception:
                    pass  # already exists, no problem

            
            # Set up RBAC
            with schema_context(tenant.schema_name):
                PermissionSeeder.seed_permissions_and_groups()
                roles = RBACService.seed_default_roles(tenant)
                
                owner_role = roles['owner']
                RBACService.assign_role_to_user(
                    user=user,
                    role=owner_role,
                )
            
            # Generate tokens
            tokens = AuthenticationService.generate_jwt_tokens(user)
            
            # Send welcome email (async in production)
            try:
                EmailService.send_welcome_email(user, company_name)
            except Exception as e:
                # Don't fail registration if welcome email fails
                pass
            
            # Clear registration data
            user.registration_data = None
            user.save()
            
            return {
                "status": "registration_complete",
                "message": "Email verified and registration completed successfully.",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "is_verified": True,
                    "is_active": True,
                },
                "tenant": {
                    "id": str(tenant.id),
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "schema_name": tenant.schema_name,
                },
                "domain": domain.domain,
                "tokens": tokens,
            }
    
    @staticmethod
    def resend_verification_code(
        email: str,
        purpose: str = 'registration',
    ) -> Dict[str, Any]:
        """
        Resend verification code.
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationError("No account found with this email.", code="USER_NOT_FOUND")
        
        if user.is_verified and purpose == 'registration':
            raise AuthenticationError(
                "Email is already verified. Please login.",
                code="ALREADY_VERIFIED"
            )
        
        success = AuthenticationService._send_verification_email(user, purpose)
        
        return {
            "status": "code_resent",
            "message": "New verification code sent to your email.",
            "email": email,
            "email_sent": success,
        }
    
    @staticmethod
    def login_user(
        *,
        email: str,
        password: str,
        tenant_slug: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:

        """
        Login user and return tenant-aware authentication data.
        """

        # ==========================================================
        # STEP 1
        # Authenticate from PUBLIC schema
        # ==========================================================

        user = authenticate(
            email=email,
            password=password
        )


        if not user:

            LoginAttempt.objects.create(
                email=email,
                tenant_slug=tenant_slug or "",
                status=LoginAttempt.FAILED,
                ip_address=ip_address,
                user_agent=user_agent or "",
                failure_reason="Invalid credentials",
            )

            raise AuthenticationError(
                "Invalid credentials"
            )


        # ==========================================================
        # STEP 2
        # Account checks
        # ==========================================================

        if not user.is_verified:

            LoginAttempt.objects.create(
                user=user,
                email=email,
                status=LoginAttempt.PENDING_VERIFICATION,
                ip_address=ip_address,
                user_agent=user_agent or "",
                failure_reason="Email not verified",
            )

            raise AuthenticationError(
                "Email not verified",
                code="EMAIL_NOT_VERIFIED"
            )


        if not user.is_active:

            LoginAttempt.objects.create(
                user=user,
                email=email,
                status=LoginAttempt.BLOCKED,
                ip_address=ip_address,
                user_agent=user_agent or "",
                failure_reason="Account disabled",
            )

            raise AuthenticationError(
                "Account is deactivated"
            )


        # ==========================================================
        # STEP 3
        # Get tenant memberships
        #
        # IMPORTANT:
        # remove public tenant
        # ==========================================================

        user_tenants = (
            user.tenants
            .exclude(
                schema_name="public"
            )
        )


        if not user_tenants.exists():

            raise AuthenticationError(
                "User is not associated with any tenant"
            )


        # ==========================================================
        # STEP 4
        # Pick active tenant
        # ==========================================================

        try:

            if tenant_slug:

                current_tenant = user_tenants.get(
                    slug=tenant_slug
                )

            else:

                current_tenant = user_tenants.first()


        except Tenant.DoesNotExist:

            raise AuthenticationError(
                f"Tenant '{tenant_slug}' not found"
            )


        # ==========================================================
        # STEP 5
        # Create JWT tokens
        # public schema
        # ==========================================================

        tokens = AuthenticationService.generate_jwt_tokens(
            user,
            device_info={
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )


        # ==========================================================
        # STEP 6
        # Load RBAC from tenant schema
        # ==========================================================

        try:

            with db_transaction.atomic():

                with schema_context(
                    current_tenant.schema_name
                ):


                    # IMPORTANT:
                    # reload user inside tenant schema

                    tenant_user = User.objects.get(
                        id=user.id
                    )


                    roles_data = (
                        RBACService.get_user_roles(
                            tenant_user,
                            current_tenant
                        )
                    )


                    permissions_data = (
                        RBACService.get_user_permissions(
                            tenant_user,
                            current_tenant
                        )
                    )


        except Exception as e:

            logger.exception(
                f"RBAC error: {e}"
            )

            roles_data = []

            permissions_data = {
                "permissions": []
            }



        # ==========================================================
        # STEP 7
        # Build tenant switch list
        # ==========================================================

        available_tenants = []


        for tenant in user_tenants:

            try:

                with db_transaction.atomic():

                    with schema_context(
                        tenant.schema_name
                    ):


                        tenant_user = User.objects.get(
                            id=user.id
                        )


                        tenant_roles = (
                            RBACService.get_user_roles(
                                tenant_user,
                                tenant
                            )
                        )


                        tenant_permissions = (
                            RBACService.get_user_permissions(
                                tenant_user,
                                tenant
                            )
                        )


                        available_tenants.append(
                            {
                                "id": str(tenant.id),

                                "name": tenant.name,

                                "slug": tenant.slug,

                                "schema_name":
                                    tenant.schema_name,


                                "roles": [
                                    role["role_slug"]
                                    for role in tenant_roles
                                ],


                                "permissions":
                                    tenant_permissions.get(
                                        "permissions",
                                        []
                                    ),


                                "is_current":
                                    tenant.id ==
                                    current_tenant.id,
                            }
                        )


            except Exception as e:

                logger.exception(
                    f"Tenant loading failed {tenant.schema_name}: {e}"
                )


                available_tenants.append(
                    {
                        "id": str(tenant.id),

                        "name": tenant.name,

                        "slug": tenant.slug,

                        "schema_name":
                            tenant.schema_name,

                        "roles": [],

                        "permissions": [],

                        "is_current":
                            tenant.id ==
                            current_tenant.id,
                    }
                )



        # ==========================================================
        # STEP 8
        # Login audit
        # ==========================================================

        LoginAttempt.objects.create(
            user=user,
            email=email,
            tenant_slug=current_tenant.slug,
            status=LoginAttempt.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent or "",
        )


        user.last_login = timezone.now()

        user.save(
            update_fields=[
                "last_login"
            ]
        )



        # ==========================================================
        # STEP 9
        # Response
        # ==========================================================

        return {

            "user": {

                "id": str(user.id),

                "email": user.email,

                "is_verified":
                    user.is_verified,

                "is_active":
                    user.is_active,

                "last_login":
                    (
                        user.last_login.isoformat()
                        if user.last_login
                        else None
                    ),
            },


            "current_tenant": {

                "id":
                    str(current_tenant.id),

                "name":
                    current_tenant.name,

                "slug":
                    current_tenant.slug,

                "schema_name":
                    current_tenant.schema_name,
            },


            "available_tenants":
                available_tenants,


            "roles":
                roles_data,


            "permissions":
                permissions_data.get(
                    "permissions",
                    []
                ),


            "tokens":
                tokens,
        }
    
    @staticmethod
    def initiate_password_reset(email: str) -> Dict[str, Any]:
        """
        Send password reset code to user's email.
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists
            return {
                "status": "code_sent",
                "message": "If the email exists, a reset code has been sent.",
            }
        
        # Invalidate old reset tokens
        PasswordResetToken.objects.filter(
            user=user,
            is_used=False,
        ).update(is_used=True)
        
        # Generate new code
        code = PasswordResetToken.generate_code()
        
        # Create token (valid for 15 minutes)
        PasswordResetToken.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        
        # Send email
        EmailService.send_password_reset(user, code)
        
        return {
            "status": "code_sent",
            "message": "If the email exists, a reset code has been sent.",
        }
    
    @staticmethod
    def verify_and_reset_password(
        email: str,
        code: str,
        new_password: str,
    ) -> Dict[str, Any]:
        """
        Verify reset code and set new password.
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationError("User not found")
        
        # Get reset token
        try:
            reset_token = PasswordResetToken.objects.get(
                user=user,
                code=code,
                is_used=False,
            )
        except PasswordResetToken.DoesNotExist:
            raise AuthenticationError("Invalid reset code")
        
        if not reset_token.is_valid():
            raise AuthenticationError("Reset code expired or too many attempts")
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.mark_as_used()
        
        # Revoke all existing tokens (force logout on all devices)
        RefreshTokenModel.objects.filter(
            user=user,
            is_valid=True,
        ).update(is_valid=False, revoked_at=timezone.now())
        
        return {
            "status": "password_reset",
            "message": "Password reset successfully. Please login with your new password.",
        }
    
    @staticmethod
    def switch_tenant(
        user: User,
        tenant_slug: str,
    ) -> Dict[str, Any]:
        """Switch to a different tenant."""
        try:
            tenant = user.tenants.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            raise AuthenticationError(f"Tenant '{tenant_slug}' not found or not accessible")
        
        with schema_context(tenant.schema_name):
            permissions_data = RBACService.get_user_permissions(user, tenant)
            roles_data = RBACService.get_user_roles(user, tenant)
        
        return {
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "schema_name": tenant.schema_name,
            },
            "roles": roles_data,
            "permissions": permissions_data["permissions"],
        }
    
    @staticmethod
    def refresh_token(refresh_token: str) -> Dict[str, str]:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            try:
                stored_token = RefreshTokenModel.objects.get(
                    token=token_hash,
                    is_valid=True,
                    expires_at__gt=timezone.now(),
                )
            except RefreshTokenModel.DoesNotExist:
                raise AuthenticationError("Token has been revoked or expired")
            
            user = User.objects.get(id=payload["user_id"])
            stored_token.revoke()
            
            return AuthenticationService.generate_jwt_tokens(user)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Refresh token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid refresh token")
    
    @staticmethod
    def logout_user(user: User, refresh_token: Optional[str] = None) -> bool:
        """Logout user by revoking refresh token."""
        if refresh_token:
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            RefreshTokenModel.objects.filter(
                token=token_hash,
                user=user,
                is_valid=True,
            ).update(is_valid=False, revoked_at=timezone.now())
        else:
            RefreshTokenModel.objects.filter(
                user=user,
                is_valid=True,
            ).update(is_valid=False, revoked_at=timezone.now())
        
        return True
    
    @staticmethod
    def get_current_user_info(user: User, tenant: Tenant) -> Dict[str, Any]:
        """Get current user's full information for the active tenant."""
        with schema_context(tenant.schema_name):
            permissions_data = RBACService.get_user_permissions(user, tenant)
            roles_data = RBACService.get_user_roles(user, tenant)
        
        user_tenants = user.tenants.all()
        available_tenants = []
        for t in user_tenants:
            with schema_context(t.schema_name):
                tenant_roles = RBACService.get_user_roles(user, t)
            
            available_tenants.append({
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "schema_name": t.schema_name,
                "roles": [r["role_slug"] for r in tenant_roles],
                "is_current": t.id == tenant.id,
            })
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "is_verified": user.is_verified,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "current_tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "schema_name": tenant.schema_name,
            },
            "available_tenants": available_tenants,
            "roles": roles_data,
            "permissions": permissions_data["permissions"],
        }


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    def __init__(self, message: str, code: str = "AUTHENTICATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)