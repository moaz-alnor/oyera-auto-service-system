"""Settings used during local application development."""

import environ

from .base import *  # noqa: F403, F405

# The private environment file is stored in the project root.
ENV_FILE = BASE_DIR.parent / ".env"  # noqa: F405

env = environ.Env()

# Load local configuration without overwriting variables already supplied
# by the operating system.
environ.Env.read_env(ENV_FILE)


# Django configuration

SECRET_KEY = env.str("DJANGO_SECRET_KEY")

DEBUG = env.bool(
    "DJANGO_DEBUG",
    default=True,
)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["127.0.0.1", "localhost"],
)


# PostgreSQL configuration

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
        "HOST": env.str(
            "POSTGRES_HOST",
            default="127.0.0.1",
        ),
        "PORT": env.int(
            "POSTGRES_PORT",
            default=5432,
        ),
        "CONN_MAX_AGE": 0,
    },
}


# Display development emails in the terminal instead of sending them.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
