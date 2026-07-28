"""Tests for supplier selectors."""

import pytest

from apps.purchasing.selectors import (
    find_possible_supplier_duplicates,
    get_supplier_by_id,
    search_suppliers,
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    deactivate_supplier,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def _create_supplier(
    *,
    context: PurchasingTestContext,
    code: str,
    name: str,
):
    """Create one supplier for selector tests."""

    return register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code=code,
            name=name,
            phone_number="+256700123456",
            email=f"{code.lower()}@example.com",
        ),
    )


@pytest.mark.django_db
def test_search_suppliers_by_code_and_name(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Find active suppliers using general search."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="CASTROL-UG",
        name="Castrol Uganda",
    )

    assert list(search_suppliers(query="castrol")) == [supplier]

    assert list(search_suppliers(query="CASTROL-UG")) == [supplier]


@pytest.mark.django_db
def test_inactive_suppliers_are_hidden_by_default(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Exclude inactive suppliers unless requested."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="INACTIVE-01",
        name="Inactive Supplier",
    )
    deactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
    )

    assert list(search_suppliers()) == []

    assert list(search_suppliers(include_inactive=True)) == [supplier]


@pytest.mark.django_db
def test_get_supplier_by_id(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return one supplier by identifier."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="LOOKUP-01",
        name="Lookup Supplier",
    )

    assert get_supplier_by_id(supplier_id=supplier.pk) == supplier


@pytest.mark.django_db
def test_find_possible_supplier_duplicates(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Detect possible duplicate supplier records."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="DUPLICATE-01",
        name="Duplicate Supplier",
    )

    duplicates = find_possible_supplier_duplicates(
        code="duplicate 01",
        name="Different Display Name",
        phone_number="",
        email="",
    )

    assert list(duplicates) == [supplier]
