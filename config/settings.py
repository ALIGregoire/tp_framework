"""
Django settings for config project.
"""

import dj_database_url
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# 🔐 SECURITY
# ========================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-&eh5&5p0c*n3g(l@d&)80$sz^66g8g&gimz)m)61@9$azs2@kh",
)

DEBUG = os.getenv("DJANGO_DEBUG", "0").lower() in ("1", "true", "yes", "y", "on")

_allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS")

if DEBUG and not _allowed_hosts_env:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [
        h.strip()
        for h in (_allowed_hosts_env or "localhost,127.0.0.1").split(",")
        if h.strip()
    ]

# ========================
# 📦 APPLICATIONS
# ========================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps tierces
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',

    # Nos applications
    'accounts',
    'tickets',
]

# ========================
# ⚙️ MIDDLEWARE
# ========================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    # 👇 Ajout pour Render
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ========================
# 🌐 URLS / WSGI
# ========================

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# ========================
# 🗄️ DATABASE (Render PostgreSQL)
# ========================

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600
    )
}

# ========================
# 🔐 AUTH USER
# ========================

AUTH_USER_MODEL = 'accounts.CustomUser'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # tu peux ajouter des templates plus tard
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ========================
# 🔥 DJANGO REST FRAMEWORK
# ========================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ========================
# 🔑 PASSWORD VALIDATION
# ========================

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

# ========================
# 🌍 CORS (Flutter)
# ========================

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        o.strip()
        for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]

# ========================
# 🌐 INTERNATIONALIZATION
# ========================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ========================
# 📁 STATIC FILES (OBLIGATOIRE)
# ========================

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Pour servir les fichiers statiques efficacement
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ========================
# 🔒 SECURITE (optionnel mais recommandé)
# ========================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
