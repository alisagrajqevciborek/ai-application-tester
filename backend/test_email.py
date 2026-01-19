"""
Test script to verify email configuration.
Run this with: python manage.py shell < test_email.py
Or: python manage.py shell, then copy-paste this code
"""
import os
from django.conf import settings
from django.core.mail import send_mail

print("\n" + "="*60)
print("EMAIL CONFIGURATION TEST")
print("="*60)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else '(empty)'}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("="*60 + "\n")

# Test email
test_email = input("Enter your email address to test: ").strip()

if not test_email:
    print("No email provided. Exiting.")
    exit()

print(f"\nSending test email to {test_email}...")

try:
    result = send_mail(
        subject='Test Email - TestFlow AI',
        message='This is a test email. If you receive this, your email configuration is working!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[test_email],
        fail_silently=False,
    )
    print(f"\n✓ Email sent successfully! Result: {result}")
    print("Check your inbox (and spam folder) for the test email.")
except Exception as e:
    print(f"\n✗ Error sending email: {e}")
    import traceback
    print("\nFull error:")
    print(traceback.format_exc())
    print("\nTroubleshooting:")
    print("1. Check your .env file has EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
    print("2. For Gmail, make sure you're using an App Password, not your regular password")
    print("3. Check that 2-Factor Authentication is enabled on your Gmail account")
    print("4. Verify EMAIL_HOST and EMAIL_PORT are correct for your email provider")

