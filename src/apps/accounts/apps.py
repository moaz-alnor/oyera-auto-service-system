"""Application configuration for the accounts module."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configure the accounts and access-management module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts and Access"
