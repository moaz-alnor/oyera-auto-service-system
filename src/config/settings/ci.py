"""Settings used by GitHub Actions continuous integration."""

import os

from .test import *  # noqa: F403, F405

# Use the temporary PostgreSQL service created by GitHub Actions.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": int(
            os.environ.get(
                "POSTGRES_PORT",
                "5432",
            )
        ),
        "CONN_MAX_AGE": 0,
    },
}
