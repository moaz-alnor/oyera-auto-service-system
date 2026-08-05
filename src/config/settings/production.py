"""Settings used by the production deployment."""

import os
from pathlib import Path

import dj_database_url

from .base import *  # noqa: F403

# Required values deliberately have no unsafe production defaults.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = False

_allowed_host_values = [
    os.environ.get("DJANGO_ALLOWED_HOSTS", ""),
    os.environ.get("RENDER_EXTERNAL_HOSTNAME", ""),
]

ALLOWED_HOSTS = [
    host
    for value in _allowed_host_values
    for host in (item.strip() for item in value.split(","))
    if host
]

if not ALLOWED_HOSTS:
    raise RuntimeError(
        "Set DJANGO_ALLOWED_HOSTS or RENDER_EXTERNAL_HOSTNAME in production."
    )


_database_url = os.environ.get(
    "DATABASE_URL",
    "",
).strip()

if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=60,
            conn_health_checks=True,
        ),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ.get(
                "POSTGRES_HOST",
                "localhost",
            ),
            "PORT": os.environ.get(
                "POSTGRES_PORT",
                "5432",
            ),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        },
    }


# Production runtime and storage configuration.
#
# WhiteNoise serves collected application static files only. User-uploaded
# media remains separate and can be placed on persistent storage.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": ("whitenoise.storage.CompressedManifestStaticFilesStorage"),
    },
}

USE_R2_STORAGE = (
    os.environ.get(
        "USE_R2_STORAGE",
        "false",
    )
    .strip()
    .lower()
    == "true"
)

if USE_R2_STORAGE:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": os.environ["R2_ACCESS_KEY_ID"],
            "secret_key": os.environ["R2_SECRET_ACCESS_KEY"],
            "bucket_name": os.environ["R2_BUCKET_NAME"],
            "endpoint_url": os.environ["R2_ENDPOINT_URL"],
            "region_name": "auto",
            "location": "media",
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,
        },
    }

STATIC_ROOT = Path(
    os.environ.get(
        "DJANGO_STATIC_ROOT",
        str(BASE_DIR / "staticfiles"),
    )
)

MEDIA_ROOT = Path(
    os.environ.get(
        "DJANGO_MEDIA_ROOT",
        str(BASE_DIR / "media"),
    )
)


# Production application logging.
#
# Logs are written to the process console so the deployment platform can
# collect, retain, search, and alert on them without application-managed files.
LOG_LEVEL = (
    os.environ.get(
        "DJANGO_LOG_LEVEL",
        "INFO",
    )
    .strip()
    .upper()
)

_ALLOWED_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

if LOG_LEVEL not in _ALLOWED_LOG_LEVELS:
    raise ValueError(
        "DJANGO_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "production": {
            "format": ("{asctime} {levelname} {name} {message}"),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "production",
            "level": LOG_LEVEL,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


# HTTPS security settings.
#
# HSTS remains environment-controlled so that it can be introduced gradually
# after HTTPS, proxy handling, domains, and subdomains have been verified.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# Trust the proxy HTTPS header only when the deployment proxy is configured
# to remove any client-supplied value and set the header itself.
if (
    os.environ.get(
        "DJANGO_TRUST_X_FORWARDED_PROTO",
        "false",
    )
    .strip()
    .lower()
    == "true"
):
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get(
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "false",
    )
    .strip()
    .lower()
    == "true"
)
SECURE_HSTS_PRELOAD = (
    os.environ.get(
        "DJANGO_SECURE_HSTS_PRELOAD",
        "false",
    )
    .strip()
    .lower()
    == "true"
)
