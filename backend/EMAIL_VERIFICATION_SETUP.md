# Email Verification Setup Guide

## Problem: Not Receiving Verification Emails

If you can sign up but don't receive verification emails, follow these steps:

### Step 1: Check Console Output

When you register, check the **Django server console** (where you run `python manage.py runserver`). 

If email is not configured, you should see:
- The verification code printed in the console
- Email configuration details
- Any error messages

**The verification code is printed to console even if email fails!**

### Step 2: Configure Email Settings

Create a `.env` file in the `backend` folder with your email credentials:

#### Option A: Gmail (Recommended for Testing)

1. Enable 2-Factor Authentication on your Google Account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Add to `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
```

#### Option B: Use Console Backend (Development Only)

For development, emails are printed to console. No configuration needed, but check your Django server terminal for the verification code.

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Step 3: Test Email Configuration

1. Restart your Django server after updating `.env`
2. Try registering a new user
3. Check:
   - Console output for verification code
   - Your email inbox (and spam folder)
   - Any error messages in console

### Step 4: Resend Verification Code

If you didn't receive the email, you can resend it:

**API Endpoint:** `POST /api/auth/resend-code`

**Request Body:**
```json
{
  "email": "your-email@example.com"
}
```

### Troubleshooting

1. **Email in console but not inbox**: Email backend is set to console. Configure SMTP settings.

2. **"Authentication failed" error**: 
   - Check email and password are correct
   - For Gmail, use App Password, not regular password

3. **"Connection refused" error**:
   - Check EMAIL_HOST and EMAIL_PORT
   - Ensure your firewall allows SMTP connections

4. **Emails go to spam**:
   - Check spam folder
   - Use a professional email service for production

### Quick Test

Run this in Django shell to test email:

```python
python manage.py shell
>>> from apps.users.utils import send_verification_email
>>> send_verification_email('test@example.com', '123456')
```

Check console output for email configuration and any errors.

