"""Tests for purchasing database models."""

import pytest
from django.core.exceptions import ValidationError

from apps.purchasing.models import Supplier
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


@pytest.mark.django_db
def test_supplier_normalizes_business_fields(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Normalise supplier identity and contact data."""

    supplier = Supplier(
        code="  auto parts 01  ",
        name="  Kampala   Auto Parts  ",
        contact_name="  Amina Musa  ",
        phone_number="  +256700123456  ",
        email="  SALES@EXAMPLE.COM  ",
        tax_identifier="  tin-1001  ",
        preferred_currency="ugx",
        payment_terms_days=30,
        created_by=purchasing_context.manager,
        updated_by=purchasing_context.manager,
    )

    supplier.full_clean()
    supplier.save()

    assert supplier.code == "AUTO-PARTS-01"
    assert supplier.normalized_code == ("AUTO-PARTS-01")
    assert supplier.name == "Kampala Auto Parts"
    assert supplier.normalized_name == ("kampala auto parts")
    assert supplier.contact_name == "Amina Musa"
    assert supplier.email == "sales@example.com"
    assert supplier.tax_identifier == "TIN-1001"
    assert supplier.preferred_currency == "UGX"


@pytest.mark.django_db
def test_supplier_rejects_invalid_currency(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require a three-character currency code."""

    supplier = Supplier(
        code="SUPPLIER-01",
        name="Supplier One",
        preferred_currency="UGANDA",
        created_by=purchasing_context.manager,
    )

    with pytest.raises(ValidationError) as exc_info:
        supplier.full_clean()

    assert "preferred_currency" in (exc_info.value.message_dict)


@pytest.mark.django_db
def test_supplier_code_must_be_unique(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent duplicate normalised supplier codes."""

    first = Supplier(
        code="AUTO-01",
        name="First Supplier",
        created_by=purchasing_context.manager,
    )
    first.full_clean()
    first.save()

    duplicate = Supplier(
        code=" auto 01 ",
        name="Second Supplier",
        created_by=purchasing_context.manager,
    )

    with pytest.raises(ValidationError) as exc_info:
        duplicate.full_clean()

    assert "normalized_code" in (exc_info.value.message_dict)
