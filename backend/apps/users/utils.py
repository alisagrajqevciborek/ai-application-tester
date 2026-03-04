"""
Utility functions for user management.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
import os

logger = logging.getLogger(__name__)


def send_verification_email(user_email, verification_code):
    """
    Send verification code email to user.
    """
    subject = 'Verify Your Email - TestFlow AI'
    message = f"""
Hello,

Thank you for registering with TestFlow AI!

Your verification code is: {verification_code}

This code will expire in 15 minutes.

If you didn't create an account, please ignore this email.

Best regards,
TestFlow AI Team
"""
    from_email = os.getenv('EMAIL_FROM', settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@testflowai.com')

    if settings.DEBUG:
        logger.debug(
            "Email configuration: backend=%s host=%s port=%s tls=%s from=%s to=%s",
            settings.EMAIL_BACKEND,
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            settings.EMAIL_USE_TLS,
            from_email,
            user_email,
        )

    try:
        result = send_mail(
            subject,
            message,
            from_email,
            [user_email],
            fail_silently=False,
        )
        logger.info("Verification email sent to %s (result=%s)", user_email, result)
        return True
    except Exception:
        logger.exception("Failed to send verification email to %s", user_email)
        return False

