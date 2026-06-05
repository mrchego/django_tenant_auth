from django.contrib import admin
from django_tenants_auth.core.admin import TimeStampedModelAdmin
from django_tenants_auth.authentication.models import (
    RefreshToken,
    LoginAttempt,
    PasswordResetToken,
)


@admin.register(RefreshToken)
class RefreshTokenAdmin(TimeStampedModelAdmin):
    list_display = ['user', 'is_valid', 'expires_at', 'created_at']
    list_filter = ['is_valid', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = TimeStampedModelAdmin.readonly_fields + ['token']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'token', 'is_valid', 'expires_at', 'revoked_at')
        }),
        ('Device Info', {
            'fields': ('device_info', 'ip_address'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['revoke_tokens']
    
    def revoke_tokens(self, request, queryset):
        """Bulk revoke selected refresh tokens."""
        from django.utils import timezone
        count = queryset.filter(is_valid=True).update(
            is_valid=False,
            revoked_at=timezone.now()
        )
        self.message_user(
            request,
            f"Successfully revoked {count} refresh token(s)."
        )
    revoke_tokens.short_description = "Revoke selected tokens"


@admin.register(LoginAttempt)
class LoginAttemptAdmin(TimeStampedModelAdmin):
    list_display = ['email', 'user', 'status', 'ip_address', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['email', 'user__email', 'ip_address']
    readonly_fields = TimeStampedModelAdmin.readonly_fields
    
    fieldsets = (
        (None, {
            'fields': ('email', 'user', 'tenant_slug', 'status')
        }),
        ('Details', {
            'fields': ('ip_address', 'user_agent', 'failure_reason'),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(TimeStampedModelAdmin):
    list_display = ['user', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email']
    readonly_fields = TimeStampedModelAdmin.readonly_fields