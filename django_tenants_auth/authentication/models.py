from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

from django_tenants_auth.core.models import TimeStampedModel


class RefreshToken(TimeStampedModel):
    """
    Store refresh tokens for JWT authentication.
    
    This allows us to invalidate tokens on logout or password change.
    In production, you might want to use Redis instead for better performance.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )
    token = models.CharField(max_length=500, unique=True, db_index=True)
    is_valid = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_valid']),
            models.Index(fields=['token']),
        ]
        verbose_name = "Refresh Token"
        verbose_name_plural = "Refresh Tokens"

    def __str__(self):
        return f"Refresh token for {self.user.email}"

    def revoke(self):
        """Revoke this refresh token."""
        self.is_valid = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_valid', 'revoked_at'])


class EmailVerificationToken(TimeStampedModel):
    """
    Store email verification tokens.
    
    Used to verify email addresses during registration and email changes.
    Token is a 6-digit code that expires after 15 minutes.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    code = models.CharField(max_length=6, db_index=True)  # 6-digit verification code
    purpose = models.CharField(
        max_length=50,
        choices=[
            ('registration', 'Registration'),
            ('email_change', 'Email Change'),
            ('password_reset', 'Password Reset'),
        ],
        default='registration'
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)  # Track verification attempts
    max_attempts = models.IntegerField(default=3)
    new_email = models.EmailField(null=True, blank=True)  # For email change

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'purpose', 'is_used']),
            models.Index(fields=['code', 'expires_at']),
        ]
        verbose_name = "Email Verification Token"
        verbose_name_plural = "Email Verification Tokens"

    def __str__(self):
        return f"Email verification for {self.user.email} - {self.purpose}"

    def is_valid(self):
        """Check if token is still valid."""
        return (
            not self.is_used and 
            self.expires_at > timezone.now() and
            self.attempts < self.max_attempts
        )

    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

    def increment_attempts(self):
        """Increment verification attempts."""
        self.attempts += 1
        self.save(update_fields=['attempts'])

    @classmethod
    def generate_code(cls):
        """Generate a random 6-digit verification code."""
        import random
        return str(random.randint(100000, 999999))


class LoginAttempt(TimeStampedModel):
    """
    Track login attempts for security auditing and brute force protection.
    """
    SUCCESS = 'success'
    FAILED = 'failed'
    BLOCKED = 'blocked'
    PENDING_VERIFICATION = 'pending_verification'
    
    STATUS_CHOICES = [
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (BLOCKED, 'Blocked'),
        (PENDING_VERIFICATION, 'Pending Verification'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='login_attempts'
    )
    email = models.EmailField()
    tenant_slug = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = "Login Attempt"
        verbose_name_plural = "Login Attempts"

    def __str__(self):
        return f"Login attempt by {self.email} - {self.status}"


class PasswordResetToken(TimeStampedModel):
    """
    Store password reset tokens.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    code = models.CharField(max_length=6, db_index=True)  # 6-digit reset code
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"

    def __str__(self):
        return f"Password reset token for {self.user.email}"

    def is_valid(self):
        """Check if token is still valid."""
        return (
            not self.is_used and 
            self.expires_at > timezone.now() and
            self.attempts < self.max_attempts
        )
        
    def mark_as_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])
    
    @classmethod
    def generate_code(cls):
        """Generate a random 6-digit reset code."""
        import random
        return str(random.randint(100000, 999999))