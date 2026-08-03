"""Settings used by the production deployment."""

import os

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


# HTTPS security settings.
#
# HSTS remains environment-controlled so that it can be introduced gradually
# after HTTPS, proxy handling, domains, and subdomains have been verified.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

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
