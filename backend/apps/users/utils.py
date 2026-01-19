"""
Utility functions for user management.
"""
from django.core.mail import send_mail
from django.conf import settings
import os


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
    
    # Debug: Print email configuration
    print(f"\n{'='*50}")
    print("EMAIL CONFIGURATION:")
    print(f"Backend: {settings.EMAIL_BACKEND}")
    print(f"Host: {settings.EMAIL_HOST}")
    print(f"Port: {settings.EMAIL_PORT}")
    print(f"TLS: {settings.EMAIL_USE_TLS}")
    print(f"From: {from_email}")
    print(f"To: {user_email}")
    print(f"Code: {verification_code}")
    print(f"{'='*50}\n")
    
    try:
        result = send_mail(
            subject,
            message,
            from_email,
            [user_email],
            fail_silently=False,
        )
        print(f"Email sent successfully! Result: {result}")
        return True
    except Exception as e:
        import traceback
        print(f"\n{'='*50}")
        print("ERROR SENDING EMAIL:")
        print(f"Error: {e}")
        print(f"Traceback:")
        print(traceback.format_exc())
        print(f"{'='*50}\n")
        return False

