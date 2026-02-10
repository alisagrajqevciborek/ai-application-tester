"""
Django settings for AI Application Tester backend.
"""
 
from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
 
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file in backend directory
# Try multiple possible locations for .env file
env_paths = [
    BASE_DIR / '.env',  # backend/.env
    BASE_DIR.parent / 'backend' / '.env',  # project/backend/.env (if nested)
    Path('.env'),  # Current directory
]
env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        env_loaded = True
        break

if not env_loaded:
    # Fallback: try loading from current directory
    load_dotenv(override=True)
 
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-vr4g-p&0a$%!0kk032q$-o6%16h_=-zggep3+o=09gpn2yu=!j')
 
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'
 
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
 
# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
   
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
   
    # Local apps
    'apps.users',
    'apps.applications',
    'apps.reports',
]
 
# Optional apps - only add if installed
try:
    import cloudinary
    if cloudinary:  # Check if import succeeded
        INSTALLED_APPS.append('cloudinary')
    import cloudinary_storage
    if cloudinary_storage:  # Check if import succeeded
        INSTALLED_APPS.append('cloudinary_storage')
except ImportError:
    pass
 
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
 
ROOT_URLCONF = 'core.urls'
 
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
 
WSGI_APPLICATION = 'core.wsgi.application'
 
# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
#
# Dev-friendly default:
# - If `DB_PASSWORD` is not provided and DEBUG is enabled, fall back to SQLite so the app can run out-of-the-box.
# - To use Postgres, set `DB_PASSWORD` (and related DB_* env vars).

DB_PASSWORD = os.getenv('DB_PASSWORD', '')

if DEBUG and not DB_PASSWORD:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'ai_app_tester'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': DB_PASSWORD,
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
 
# Custom User Model
AUTH_USER_MODEL = 'users.User'
 
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
 
# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
 
# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
 
# Media files (using Cloudinary if available, otherwise local)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
 
try:
    import cloudinary_storage
    if cloudinary_storage:  # Check if import succeeded
        DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    else:
        DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
except ImportError:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
 
# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
 
# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
}
 
# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}
 
# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
 
CORS_ALLOW_CREDENTIALS = True
 
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
 
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
 
# Email Configuration
# Default to console backend for development, but use SMTP if credentials are provided
email_backend = os.getenv('EMAIL_BACKEND', '')
if not email_backend:
    # Auto-detect: use SMTP if credentials are provided, otherwise use console
    if os.getenv('EMAIL_HOST_USER') and os.getenv('EMAIL_HOST_PASSWORD'):
        email_backend = 'django.core.mail.backends.smtp.EmailBackend'
    else:
        email_backend = 'django.core.mail.backends.console.EmailBackend'
 
EMAIL_BACKEND = email_backend
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_FROM', EMAIL_HOST_USER or 'noreply@testflowai.com')
 
# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
 
# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', ''),
}

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')  # Default to GPT-4o for vision capabilities

# Jira Configuration
JIRA_URL = os.getenv('JIRA_URL', '')
JIRA_EMAIL = os.getenv('JIRA_EMAIL', '')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', '')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY', '')
JIRA_ISSUE_TYPE = os.getenv('JIRA_ISSUE_TYPE', 'Task')