"""
Django settings — SAMU 192 (Sistema de Estoque, Medicamentos e Logística).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-samu-192-local-dev-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "https://*.preview.emergentagent.com",
    "https://*.emergentagent.com",
    "https://*.emergentcf.cloud",
    "https://*.preview.emergentcf.cloud",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://localhost:8001",
    "http://localhost:8765",
]

# Prefixo /api só no preview (server.py define SAMU_SCRIPT_NAME). Local/desktop/rede: raiz.
FORCE_SCRIPT_NAME = os.environ.get("SAMU_SCRIPT_NAME") or None
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AgendadorFirebaseMiddleware",
]

ROOT_URLCONF = "samu.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.sidebar_context",
                "core.context_processors.configuracao_context",
            ],
        },
    },
]

WSGI_APPLICATION = "samu.wsgi.application"
ASGI_APPLICATION = "samu.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 4}},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "medicamentos_lista"
LOGOUT_REDIRECT_URL = "login"

# Sessão persiste entre restarts.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

MESSAGE_TAGS = {
    10: "debug",
    20: "info",
    25: "success",
    30: "warning",
    40: "error",
}
