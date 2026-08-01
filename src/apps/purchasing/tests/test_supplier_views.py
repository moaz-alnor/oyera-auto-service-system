"""Tests for supplier-management browser views."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.purchasing.models import Supplier
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _supplier_data(
    *,
    code: str = "VIEW-PARTS-01",
    name: str = "View Parts Uganda",
) -> dict[str, str]:
    """Return valid supplier browser data."""

    return {
        "code": code,
        "name": name,
        "contact_name": "Amina Musa",
        "phone_number": "+256700123456",
        "email": "supplier@example.com",
        "address": "Industrial Area, Kampala",
        "tax_identifier": "TIN-VIEW-001",
        "payment_terms_days": "30",
        "preferred_currency": "UGX",
        "notes": "Supplier browser test.",
    }


def _create_supplier(
    *,
    context: PurchasingTestContext,
    code: str = "EXISTING-PARTS",
    name: str = "Existing Parts Uganda",
) -> Supplier:
    """Create one supplier through its service."""

    return register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code=code,
            name=name,
            contact_name="Sarah Nakato",
            phone_number="+256700555222",
            email="existing@example.com",
            address="Kampala, Uganda",
            tax_identifier="TIN-EXISTING-01",
            payment_terms_days=30,
            preferred_currency="UGX",
            notes="Existing supplier.",
        ),
    )


def test_supplier_urls_reverse() -> None:
    """Reverse all supplier-management routes."""

    assert reverse("purchasing:supplier_list") == "/purchasing/suppliers/"

    assert reverse("purchasing:supplier_create") == "/purchasing/suppliers/new/"

    assert (
        reverse(
            "purchasing:supplier_detail",
            args=(1,),
        )
        == "/purchasing/suppliers/1/"
    )

    assert (
        reverse(
            "purchasing:supplier_update",
            args=(1,),
        )
        == "/purchasing/suppliers/1/edit/"
    )

    assert reverse(
        "purchasing:supplier_deactivate",
        args=(1,),
    ) == ("/purchasing/suppliers/1/deactivate/")

    assert reverse(
        "purchasing:supplier_reactivate",
        args=(1,),
    ) == ("/purchasing/suppliers/1/reactivate/")


def test_anonymous_user_is_redirected(
    client: Client,
) -> None:
    """Require authentication for supplier records."""

    response = client.get(reverse("purchasing:supplier_list"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


def test_receptionist_can_view_suppliers(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Allow read-only Purchasing access."""

    supplier = _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    list_response = client.get(reverse("purchasing:supplier_list"))
    detail_response = client.get(
        reverse(
            "purchasing:supplier_detail",
            args=(supplier.pk,),
        )
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert list(list_response.context["suppliers"]) == [supplier]
    assert detail_response.context["supplier"] == supplier


def test_manager_registers_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Register a supplier through the browser."""

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse("purchasing:supplier_create"),
        _supplier_data(),
    )

    supplier = Supplier.objects.get(code="VIEW-PARTS-01")

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:supplier_detail",
        args=(supplier.pk,),
    )
    assert supplier.supplier_number == (f"SUP-{supplier.pk:06d}")
    assert supplier.preferred_currency == "UGX"


def test_supplier_duplicate_requires_confirmation(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require confirmation before saving a duplicate."""

    _create_supplier(
        context=purchasing_context,
        code="ORIGINAL-PARTS",
        name="Duplicate Parts Uganda",
    )

    client.force_login(purchasing_context.manager)

    data = _supplier_data(
        code="SECOND-PARTS",
        name="Duplicate Parts Uganda",
    )

    warning_response = client.post(
        reverse("purchasing:supplier_create"),
        data,
    )

    assert warning_response.status_code == 200
    assert warning_response.context["duplicate_confirmation_required"] is True
    assert Supplier.objects.count() == 1

    data["confirm_duplicate"] = "on"

    confirmed_response = client.post(
        reverse("purchasing:supplier_create"),
        data,
    )

    assert confirmed_response.status_code == 302
    assert Supplier.objects.count() == 2


def test_manager_updates_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Update supplier information through the browser."""

    supplier = _create_supplier(context=purchasing_context)
    data = _supplier_data(
        code="UPDATED-PARTS",
        name="Updated Parts Uganda",
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_update",
            args=(supplier.pk,),
        ),
        data,
    )

    supplier.refresh_from_db()

    assert response.status_code == 302
    assert supplier.code == "UPDATED-PARTS"
    assert supplier.name == ("Updated Parts Uganda")


def test_manager_deactivates_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Deactivate a supplier through POST."""

    supplier = _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_deactivate",
            args=(supplier.pk,),
        )
    )

    supplier.refresh_from_db()

    assert response.status_code == 302
    assert supplier.is_active is False


def test_manager_reactivates_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reactivate a supplier through POST."""

    supplier = _create_supplier(context=purchasing_context)
    supplier.is_active = False
    supplier.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_reactivate",
            args=(supplier.pk,),
        )
    )

    supplier.refresh_from_db()

    assert response.status_code == 302
    assert supplier.is_active is True


def test_receptionist_cannot_register_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep supplier writes under management."""

    client.force_login(purchasing_context.receptionist)

    response = client.post(
        reverse("purchasing:supplier_create"),
        _supplier_data(),
    )

    assert response.status_code == 403
    assert Supplier.objects.count() == 0


def test_missing_supplier_returns_404(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return HTTP 404 for an unknown supplier."""

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_detail",
            args=(999999,),
        )
    )

    assert response.status_code == 404
