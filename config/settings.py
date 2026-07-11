import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCT_NAME = os.getenv("PRODUCT_NAME", "Morse")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-mvp-dev-key-change-in-production",
)

DEBUG = str(os.getenv("DEBUG", "True")).lower() in ("1", "true", "yes", "on")

_hosts = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()] or (
    ["*"] if DEBUG else []
)

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8002").rstrip("/")

# When the widget is embedded on a customer's site, iframe sessions may need
# cross-site cookies. Set WIDGET_EMBED_CROSS_ORIGIN=1 in production (with HTTPS).
WIDGET_EMBED_CROSS_ORIGIN = os.getenv("WIDGET_EMBED_CROSS_ORIGIN", "").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "websites",
    "accounts",
    "contacts",
    "inbox",
    "knowledge",
    "widget",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "websites.middleware.WebsiteMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

SMS_IR_API_KEY = os.getenv("SMS_IR_API_KEY", "")
SMS_IR_LINE_NUMBER = os.getenv("SMS_IR_LINE_NUMBER", "")
SMS_IR_VERIFY_TEMPLATE_ID = os.getenv("SMS_IR_VERIFY_TEMPLATE_ID", "")

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:inbox"
LOGOUT_REDIRECT_URL = "accounts:login"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Cross-site cookies for embedded widget iframe + admin login on local HTTP.
if WIDGET_EMBED_CROSS_ORIGIN:
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
elif DEBUG:
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = False
else:
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True

X_FRAME_OPTIONS = "SAMEORIGIN"
