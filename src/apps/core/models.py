"""Shared database models used across business modules."""

from django.db import models


class TimeStampedModel(models.Model):
    """Provide creation and update timestamps to business records."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        """Prevent creation of a database table for this base model."""

        abstract = True
