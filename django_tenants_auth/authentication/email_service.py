import logging
from typing import Optional
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending transactional emails.
    
    Handles email verification, password reset, welcome emails, etc.
    """
    
    @staticmethod
    def send_email_verification(user, verification_code: str) -> bool:
        """
        Send email verification code to user.
        
        Template similar to GitHub's verification email:
        
        Subject: Please verify your identity, {username}
        
        Body:
        Here is your {app_name} verification code:
        
        {verification_code}
        
        This code is valid for 15 minutes and can only be used once.
        
        Please don't share this code with anyone: we'll never ask for it 
        on the phone or via email.
        
        Thanks,
        The {app_name} Team
        """
        try:
            subject = f"Please verify your identity, {user.email.split('@')[0]}"
            
            # HTML email template
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #24292e;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        border: 1px solid #e1e4e8;
                        border-radius: 6px;
                        padding: 32px;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 24px;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    .content {{
                        font-size: 16px;
                    }}
                    .code-box {{
                        background-color: #f6f8fa;
                        border: 1px solid #e1e4e8;
                        border-radius: 6px;
                        padding: 16px;
                        margin: 24px 0;
                        text-align: center;
                    }}
                    .verification-code {{
                        font-size: 32px;
                        font-weight: bold;
                        letter-spacing: 8px;
                        color: #24292e;
                        font-family: 'Courier New', monospace;
                    }}
                    .info {{
                        font-size: 14px;
                        color: #586069;
                        margin-top: 16px;
                    }}
                    .footer {{
                        margin-top: 32px;
                        padding-top: 16px;
                        border-top: 1px solid #e1e4e8;
                        font-size: 12px;
                        color: #586069;
                    }}
                    .warning {{
                        color: #cb2431;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <a href="#" class="logo">{settings.APP_NAME}</a>
                    </div>
                    
                    <div class="content">
                        <p>Please verify your identity, <strong>{user.email.split('@')[0]}</strong></p>
                        
                        <p>Here is your {settings.APP_NAME} verification code:</p>
                        
                        <div class="code-box">
                            <div class="verification-code">{verification_code}</div>
                        </div>
                        
                        <div class="info">
                            <p>⏰ This code is valid for <strong>15 minutes</strong> and can only be used once.</p>
                            <p class="warning">🔒 Please don't share this code with anyone: we'll never ask for it on the phone or via email.</p>
                        </div>
                        
                        <p>If you didn't request this code, you can safely ignore this email.</p>
                    </div>
                    
                    <div class="footer">
                        <p>Thanks,<br>The {settings.APP_NAME} Team</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            plain_message = f"""
Please verify your identity, {user.email.split('@')[0]}

Here is your {settings.APP_NAME} verification code:

{verification_code}

This code is valid for 15 minutes and can only be used once.

Please don't share this code with anyone: we'll never ask for it on the phone or via email.

If you didn't request this code, you can safely ignore this email.

Thanks,
The {settings.APP_NAME} Team
            """
            
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(plain_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Verification email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(user, tenant_name: str) -> bool:
        """
        Send welcome email after successful registration and verification.
        """
        try:
            subject = f"Welcome to {settings.APP_NAME} - {tenant_name}"
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #24292e;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        border: 1px solid #e1e4e8;
                        border-radius: 6px;
                        padding: 32px;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 24px;
                    }}
                    .welcome-icon {{
                        font-size: 48px;
                        margin-bottom: 16px;
                    }}
                    h1 {{
                        font-size: 24px;
                        margin-bottom: 8px;
                    }}
                    .content {{
                        font-size: 16px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #2ea44f;
                        color: white;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 6px;
                        margin: 16px 0;
                    }}
                    .footer {{
                        margin-top: 32px;
                        padding-top: 16px;
                        border-top: 1px solid #e1e4e8;
                        font-size: 12px;
                        color: #586069;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="welcome-icon">🎉</div>
                        <h1>Welcome to {settings.APP_NAME}!</h1>
                    </div>
                    
                    <div class="content">
                        <p>Hi {user.email.split('@')[0]},</p>
                        
                        <p>Your account for <strong>{tenant_name}</strong> has been successfully created and verified.</p>
                        
                        <p>You can now start using {settings.APP_NAME} to manage your business operations.</p>
                        
                        <p>If you have any questions, please don't hesitate to contact our support team.</p>
                    </div>
                    
                    <div class="footer">
                        <p>Best regards,<br>The {settings.APP_NAME} Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(html_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Welcome email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset(user, reset_code: str) -> bool:
        """
        Send password reset code to user.
        """
        try:
            subject = f"Password Reset Code - {settings.APP_NAME}"
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #24292e;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        border: 1px solid #e1e4e8;
                        border-radius: 6px;
                        padding: 32px;
                    }}
                    .code-box {{
                        background-color: #f6f8fa;
                        border: 1px solid #e1e4e8;
                        border-radius: 6px;
                        padding: 16px;
                        margin: 24px 0;
                        text-align: center;
                    }}
                    .verification-code {{
                        font-size: 32px;
                        font-weight: bold;
                        letter-spacing: 8px;
                        color: #24292e;
                        font-family: 'Courier New', monospace;
                    }}
                    .warning {{
                        color: #cb2431;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Password Reset Request</h2>
                    <p>You have requested to reset your password for {settings.APP_NAME}.</p>
                    
                    <p>Here is your password reset code:</p>
                    
                    <div class="code-box">
                        <div class="verification-code">{reset_code}</div>
                    </div>
                    
                    <p>⏰ This code is valid for <strong>15 minutes</strong>.</p>
                    <p class="warning">🔒 If you didn't request this, please ignore this email and ensure your account is secure.</p>
                </div>
            </body>
            </html>
            """
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(html_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False