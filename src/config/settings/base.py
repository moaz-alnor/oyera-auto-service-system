"""Shared Django settings for all application environments."""

from pathlib import Path

# The src/ directory containing manage.py.
BASE_DIR = Path(__file__).resolve().parents[2]


# Application definition

INSTALLED_APPS = [
    # Django applications.
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project applications.
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.vehicles.apps.VehiclesConfig",
    "apps.service_catalogue.apps.ServiceCatalogueConfig",
    "apps.product_catalogue.apps.ProductCatalogueConfig",
    "apps.jobs.apps.JobsConfig",
    "apps.quotations.apps.QuotationsConfig",
    "apps.workshop.apps.WorkshopConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.billing.apps.BillingConfig",
]

# Use the project-specific employee account model.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]


# Internationalization

LANGUAGE_CODE = "en-us"

# The business operates in Uganda.
TIME_ZONE = "Africa/Kampala"

USE_I18N = True
USE_TZ = True


# Static and uploaded files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# Default primary-key type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication navigation

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"
