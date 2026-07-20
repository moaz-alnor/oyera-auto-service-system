"""Database models for user accounts and access management."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Represent an employee who can access the application.

    The model extends Django's standard user implementation so the project
    can add business-specific fields without replacing the authentication
    system later.
    """

    phone_number = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Employee contact number, including the country code when used.",
    )

    def __str__(self) -> str:
        """Return the employee's name or username for display."""

        full_name = self.get_full_name().strip()
        return full_name or self.username
