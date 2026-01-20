"""
Quick email test - run this to test your email configuration
Usage: python manage.py shell
Then: exec(open('test_email_simple.py').read())
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("\n" + "="*60)
print("TESTING EMAIL CONFIGURATION")
print("="*60)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'EMPTY!'}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("="*60)

if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
    print("\n❌ ERROR: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is empty!")
    print("   Check your .env file has these values set.")
else:
    print(f"\n✓ Sending test email to {settings.EMAIL_HOST_USER}...")
    try:
        result = send_mail(
            subject='Test Email from TestFlow AI',
            message='If you receive this, your email configuration is working!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        print(f"✓ Email sent! Result: {result}")
        print("   Check your inbox (and spam folder) for the test email.")
    except Exception as e:
        print(f"\n❌ ERROR sending email:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        print("\nFull error details:")
        traceback.print_exc()
        print("\nCommon fixes:")
        print("1. Make sure you're using an App Password (not regular password)")
        print("2. Verify 2-Factor Authentication is enabled on Gmail")
        print("3. Check that EMAIL_HOST_USER matches your Gmail address")
        print("4. Restart the Django server after changing .env")

print("="*60 + "\n")

