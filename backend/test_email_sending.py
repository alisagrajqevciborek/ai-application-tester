"""
Test script to check email configuration and send a test email.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from apps.users.utils import send_verification_email

print("\n" + "="*60)
print("EMAIL CONFIGURATION TEST")
print("="*60)

print(f"\nBackend: {settings.EMAIL_BACKEND}")
print(f"Host: {settings.EMAIL_HOST}")
print(f"Port: {settings.EMAIL_PORT}")
print(f"TLS: {settings.EMAIL_USE_TLS}")
print(f"From Email: {settings.EMAIL_HOST_USER}")
print(f"Password Set: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")

# Check if password has spaces (Gmail app passwords shouldn't have spaces)
if settings.EMAIL_HOST_PASSWORD:
    if ' ' in settings.EMAIL_HOST_PASSWORD:
        print(f"\n⚠️  WARNING: Email password contains spaces!")
        print(f"   Gmail app passwords should NOT have spaces.")
        print(f"   Current password: '{settings.EMAIL_HOST_PASSWORD}'")
        print(f"   Remove spaces in .env file: EMAIL_HOST_PASSWORD=qyicaqtyxlfccut")
    else:
        print(f"\n✅ Password format looks correct (no spaces)")

print("\n" + "="*60)
print("TESTING EMAIL SEND")
print("="*60)

# Test email sending
test_email = input("\nEnter your email address to test: ").strip()
if test_email:
    print(f"\nSending test email to {test_email}...")
    result = send_verification_email(test_email, "123456")
    
    if result:
        print("\n✅ Email sent successfully!")
        print("   Check your inbox (and spam folder)")
    else:
        print("\n❌ Email sending failed!")
        print("   Check the error messages above")
        print("\nCommon issues:")
        print("   1. Gmail app password expired or incorrect")
        print("   2. 2-factor authentication not enabled")
        print("   3. 'Less secure app access' needs to be enabled")
        print("   4. Password has spaces (should be removed)")
else:
    print("\nNo email provided, skipping test.")

print("\n" + "="*60)

