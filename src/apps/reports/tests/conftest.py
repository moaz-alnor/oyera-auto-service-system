"""Shared fixtures for operational-report tests."""

from apps.billing.tests.conftest import (
    billing_context,
)
from apps.inventory.tests.conftest import (
    inventory_context,
)
from apps.purchasing.tests.conftest import (
    purchasing_context,
)
from apps.workshop.tests.conftest import (
    workshop_execution_context,
)

__all__ = (
    "billing_context",
    "inventory_context",
    "purchasing_context",
    "workshop_execution_context",
)
