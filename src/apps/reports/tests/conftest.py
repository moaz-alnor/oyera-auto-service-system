"""Shared fixtures for operational-report tests."""

from apps.billing.tests.conftest import (
    billing_context,
)
from apps.inventory.tests.conftest import (
    inventory_context,
)
from apps.workshop.tests.conftest import (
    workshop_execution_context,
)

__all__ = (
    "billing_context",
    "inventory_context",
    "workshop_execution_context",
)
