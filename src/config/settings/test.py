"""Settings used by automated tests."""

from .base import *  # noqa: F403

SECRET_KEY = "test-environment-secret-key"

DEBUG = False

ALLOWED_HOSTS = ["testserver"]


# Temporary fast test database.
# We may replace this with PostgreSQL tests during Step 8.5.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}


# Faster password hashing for automated tests only.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
