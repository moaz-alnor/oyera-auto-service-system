"""Tests for supplier application services."""

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    UpdateSupplierCommand,
    deactivate_supplier,
    reactivate_supplier,
    register_supplier,
    update_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def _register_command(
    *,
    code: str = "AUTO-PARTS-01",
) -> RegisterSupplierCommand:
    """Return valid supplier registration input."""

    return RegisterSupplierCommand(
        code=code,
        name="Kampala Auto Parts",
        contact_name="Amina Musa",
        phone_number="+256700123456",
        email="sales@example.com",
        address="Kampala, Uganda",
        tax_identifier="TIN-1001",
        payment_terms_days=30,
        preferred_currency="UGX",
        notes="Primary parts supplier.",
    )


@pytest.mark.django_db
def test_manager_registers_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Register a supplier through the service."""

    supplier = register_supplier(
        actor=purchasing_context.manager,
        command=_register_command(),
    )

    assert supplier.supplier_number == "SUP-000001"
    assert supplier.code == "AUTO-PARTS-01"
    assert supplier.is_active is True
    assert supplier.created_by == (purchasing_context.manager)


@pytest.mark.django_db
def test_receptionist_cannot_register_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject supplier creation without permission."""

    with pytest.raises(PermissionDenied):
        register_supplier(
            actor=purchasing_context.receptionist,
            command=_register_command(),
        )


@pytest.mark.django_db
def test_manager_updates_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Update supplier contact and payment terms."""

    supplier = register_supplier(
        actor=purchasing_context.manager,
        command=_register_command(),
    )

    supplier = update_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
        command=UpdateSupplierCommand(
            code="AUTO-PARTS-01",
            name="Kampala Auto Parts Limited",
            contact_name="Musa Ahmed",
            phone_number="+256700987654",
            email="accounts@example.com",
            address="Industrial Area, Kampala",
            tax_identifier="TIN-1001",
            payment_terms_days=45,
            preferred_currency="UGX",
            notes="Updated supplier terms.",
        ),
    )

    assert supplier.name == ("Kampala Auto Parts Limited")
    assert supplier.payment_terms_days == 45
    assert supplier.updated_by == (purchasing_context.manager)


@pytest.mark.django_db
def test_manager_deactivates_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Deactivate a supplier without deleting it."""

    supplier = register_supplier(
        actor=purchasing_context.manager,
        command=_register_command(),
    )

    supplier = deactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
    )

    assert supplier.is_active is False


@pytest.mark.django_db
def test_manager_reactivates_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reactivate a previously inactive supplier."""

    supplier = register_supplier(
        actor=purchasing_context.manager,
        command=_register_command(),
    )
    deactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
    )

    supplier = reactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
    )

    assert supplier.is_active is True


@pytest.mark.django_db
def test_duplicate_supplier_code_is_rejected(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject duplicate normalised supplier codes."""

    register_supplier(
        actor=purchasing_context.manager,
        command=_register_command(),
    )

    with pytest.raises(ValidationError):
        register_supplier(
            actor=purchasing_context.manager,
            command=_register_command(code=" auto parts 01 "),
        )
