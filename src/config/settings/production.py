"""Settings used by the production deployment."""

import os
from pathlib import Path

from .base import *  # noqa: F403

# Required values deliberately have no unsafe production defaults.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
    if host.strip()
]


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
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
