# Quick Fix Guide

## Issue 1: Email Verification Not Working ✅

### Immediate Solution: Check Console for Verification Code

When you register, the **verification code is printed to the Django server console** even if email fails!

1. Look at the terminal where you run `python manage.py runserver`
2. You'll see output like:
   ```
   ⚠️  WARNING: Failed to send verification email to user@example.com
      Verification code: 123456
   ```
3. **Use that code** to verify your email via the frontend or API

### To Actually Receive Emails:

1. Create `backend/.env` file with:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

2. For Gmail, get an App Password: https://myaccount.google.com/apppasswords

3. Restart Django server

### Resend Code Endpoint

If you need a new code:
```
POST /api/auth/resend-code
Body: {"email": "your-email@example.com"}
```

## Issue 2: Database Tables Different ✅

All migrations are applied! Your database should have these tables:
- `users`
- `applications` 
- `test_runs`
- `screenshots`

If you see different tables than your friend:

1. **Check you're using the same database**:
   - Verify `DB_NAME`, `DB_HOST`, `DB_USER` in `.env`
   - Make sure you're both connecting to the same PostgreSQL database

2. **Check for schema differences**:
   ```sql
   -- In PostgreSQL
   \dt
   ```
   Compare table lists

3. **If tables are missing**, run:
   ```bash
   python manage.py migrate
   ```

4. **If tables exist but migrations show as unapplied**, use:
   ```bash
   python manage.py migrate --fake
   ```
   (Only if tables already exist!)

## Quick Test

Test email sending:
```bash
python manage.py shell
>>> from apps.users.utils import send_verification_email
>>> send_verification_email('test@example.com', '123456')
```

Check the console output for email configuration details.

