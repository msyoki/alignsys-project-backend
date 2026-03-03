"""
Django settings for auth_service project.
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "expire-trials-every-hour": {
        "task": "accounts.tasks.check_and_expire_trials",
        "schedule": crontab(minute=0, hour="*"),  # every hour
    },
}

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-changeme')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASE = os.getenv('DATABASE', 'sqlite')

if DATABASE == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'auth_service'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'password'),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.getenv('SQLITE_PATH', BASE_DIR / 'auth.db'),
        }
    }

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
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'



STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

WHITENOISE_USE_FINDERS = True




# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Simple JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
}

# Swagger/OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Auth Service API',
    'DESCRIPTION': 'Authentication service with user and organization management',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SCHEMAS': {
        'Bearer': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        },
    },
    'SECURITY': [
        {'Bearer': []},
    ],
}

# ----------------------------
# CORS & CSRF
# ----------------------------
frontend_domains = os.getenv(
    'FRONTEND_DOMAINS',
    'http://localhost:3000,http://localhost:8000,https://alignsys.tech,https://edms.alignsys.tech,https://dss.alignsys.tech'
)
FRONTEND_DOMAINS_LIST = [d.strip() for d in frontend_domains.split(',')]

# CORS
CORS_ALLOWED_ORIGINS = FRONTEND_DOMAINS_LIST
CORS_ALLOW_CREDENTIALS = True

# Custom JWT settings (legacy - keeping for backward compatibility with other code)
JWT_SECRET_KEY = SECRET_KEY
JWT_ALGORITHM = os.getenv('ALGORITHM', 'HS256')
JWT_ACCESS_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
JWT_REFRESH_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))

# Domain Auth
DOMAIN_AUTH_URL = os.getenv('DOMAIN_AUTH_URL')

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('SMTP_HOST', 'your-smtp-host.com')
EMAIL_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('SMTP_USERNAME', 'your-email@example.com')
EMAIL_HOST_PASSWORD = os.getenv('SMTP_PASSWORD', 'your-email-password')
DEFAULT_FROM_EMAIL = os.getenv('SMTP_MAIL_FROM', 'noreply@yourapp.com')

# Frontend URL for verification links
FRONTEND_URL = 'https://dev.alignsys.tech'  # Change to your frontend URL


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',  # Make sure logs/ directory exists
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts': {  # Your app name
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}