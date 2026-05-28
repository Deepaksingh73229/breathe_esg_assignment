"""
Django settings for Breathe ESG Carbon Accounting Platform.

Design Philosophy:
- Multi-tenancy at the application layer (Organization-scoped queries everywhere)
- PostgreSQL with JSONB for semi-structured raw data storage
- Immutable raw uploads with SHA-256 checksums for audit integrity
- All business models use UUID primary keys (prevents enumeration, works in distributed systems)
- Timezone-aware datetimes throughout (critical for cross-timezone audit accuracy)
"""

import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Load .env for local development. In production, environment vars come from the host.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-key-CHANGE-in-production-!@#$%")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Allowed hosts parsing: handle comma-separated string from env, fallback to safe defaults
allowed_hosts_raw = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(",") if host.strip()]

# Add Render wildcard for reliability in free-tier environments
if not DEBUG:
    ALLOWED_HOSTS.append(".onrender.com")

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",   # Token auth for API clients (Postman, React)
    "corsheaders",
    "django_filters",
]

# Ordered by dependency — least-dependent first to avoid circular import issues.
LOCAL_APPS = [
    "apps.core",            # Base models, mixins (no local deps)
    "apps.organizations",   # Multi-tenancy root
    "apps.facilities",      # Plant/office mapping
    "apps.factors",         # Versioned emission factors
    "apps.ingestion",       # Raw data pipeline
    "apps.activities",      # Normalized golden records + review workflow
    "apps.audit",           # Immutable audit trail
    "apps.dashboard",       # Read-only aggregation layer
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",       # Must come before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Captures client IP + User-Agent for AuditLog entries
    "apps.audit.middleware.AuditMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =============================================================================
# DATABASE
# =============================================================================
# PostgreSQL is mandatory:
#   - JSONB fields for RawDataRow.raw_payload and co2e_calculation_audit
#   - ArrayField for Facility.utility_account_numbers
#   - Robust ACID transactions for the audit trail
db_url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")

if db_url:
    DATABASES = {
        "default": dj_database_url.parse(
            db_url,
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# =============================================================================
# AUTH & PASSWORDS
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================================================================
# I18N / TIMEZONE
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True   # Always use tz-aware datetimes — critical for cross-timezone audit accuracy

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"   # Where raw CSV/JSON uploads are stored

# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,

    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# =============================================================================
# CORS
# =============================================================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if os.getenv("FRONTEND_URL"):
    CORS_ALLOWED_ORIGINS.append(os.getenv("FRONTEND_URL"))

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# LOGGING
# =============================================================================
os.makedirs(BASE_DIR / "logs", exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "django.log"),
            "maxBytes": 10 * 1024 * 1024,   # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO"},
        "apps.ingestion": {"handlers": ["console", "file"], "level": "DEBUG"},
        "apps.activities": {"handlers": ["console", "file"], "level": "DEBUG"},
    },
}