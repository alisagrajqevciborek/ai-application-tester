# Email Configuration Guide

To send real verification emails, you need to configure SMTP settings.

## Quick Setup

1. Create a `.env` file in the `backend` folder (copy from `.env.example`)
2. Add your email credentials
3. Restart the Django server

## Gmail Setup (Recommended)

### Step 1: Enable 2-Factor Authentication
1. Go to your Google Account settings
2. Enable 2-Factor Authentication

### Step 2: Generate App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Select "Mail" and "Other (Custom name)"
3. Enter "TestFlow AI" as the name
4. Click "Generate"
5. Copy the 16-character password (no spaces)

### Step 3: Configure .env file
Create `backend/.env` with:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
```

## Other Email Providers

### Outlook/Hotmail
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@outlook.com
EMAIL_HOST_PASSWORD=your-password
EMAIL_FROM=your-email@outlook.com
```

### Yahoo
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yahoo.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_FROM=your-email@yahoo.com
```

## Testing

After configuration:
1. Restart the Django server
2. Try registering a new account
3. Check your email inbox (and spam folder)

## Troubleshooting

- **"Authentication failed"**: Check your email and password are correct
- **"Connection refused"**: Check EMAIL_HOST and EMAIL_PORT
- **Gmail "Less secure app"**: Use App Password instead of regular password
- **Emails in spam**: Check spam folder, or use a professional email service

## Development Mode

If you don't configure email, the system will automatically use console backend and print emails to the terminal where the server is running.

