"""Tests for supplier templates and Purchasing navigation."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    deactivate_supplier,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _create_supplier(
    *,
    context: PurchasingTestContext,
    code: str = "TEMPLATE-PARTS",
    name: str = "Template Parts Uganda",
):
    """Create one supplier for template tests."""

    return register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code=code,
            name=name,
            contact_name="Amina Musa",
            phone_number="+256700123456",
            email="accounts@template.example",
            address="Industrial Area, Kampala",
            tax_identifier="TIN-TEMPLATE-001",
            payment_terms_days=30,
            preferred_currency="UGX",
            notes="Supplier template test.",
        ),
    )


def _supplier_form_data(
    *,
    code: str,
    name: str,
) -> dict[str, str]:
    """Return valid supplier form input."""

    return {
        "code": code,
        "name": name,
        "contact_name": "Sarah Nakato",
        "phone_number": "+256700555222",
        "email": "duplicate@example.com",
        "address": "Kampala, Uganda",
        "tax_identifier": "TIN-DUPLICATE-001",
        "payment_terms_days": "30",
        "preferred_currency": "UGX",
        "notes": "Duplicate template test.",
    }


def test_manager_supplier_list_displays_actions_and_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display supplier data and management actions."""

    supplier = _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:supplier_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier.supplier_number in content
    assert supplier.code in content
    assert supplier.name in content
    assert supplier.contact_name in content
    assert "Register supplier" in content
    assert "Supplier invoices" in content
    assert 'href="/purchasing/suppliers/"' in content


def test_receptionist_supplier_list_is_read_only(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Hide supplier-write controls from Receptionist."""

    supplier = _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    response = client.get(reverse("purchasing:supplier_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier.name in content
    assert "Register supplier" not in content
    assert "Purchasing" in content


def test_supplier_form_displays_duplicate_warning(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display matching supplier evidence before saving."""

    existing_supplier = _create_supplier(
        context=purchasing_context,
        code="ORIGINAL-TEMPLATE",
        name="Duplicate Template Parts",
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse("purchasing:supplier_create"),
        _supplier_form_data(
            code="SECOND-TEMPLATE",
            name="Duplicate Template Parts",
        ),
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Possible duplicate supplier" in content
    assert existing_supplier.supplier_number in content
    assert existing_supplier.code in content
    assert 'name="confirm_duplicate"' in content
    assert 'value="true"' in content
    assert "Confirm and save" in content


def test_supplier_detail_displays_profile_and_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display supplier profile and Manager actions."""

    supplier = _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_detail",
            args=(supplier.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier.supplier_number in content
    assert supplier.code in content
    assert supplier.contact_name in content
    assert supplier.phone_number in content
    assert supplier.email in content
    assert supplier.tax_identifier in content

    normalised_content = " ".join(content.split())

    assert "30 days" in normalised_content
    assert "UGX" in content
    assert "Edit supplier" in content
    assert "Deactivate supplier" in content
    assert "Reactivate supplier" not in content
    assert "No purchase orders" in content
    assert "No supplier invoices" in content


def test_inactive_supplier_detail_displays_reactivation(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display inactive warning and reactivation action."""

    supplier = _create_supplier(context=purchasing_context)

    deactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_detail",
            args=(supplier.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "This supplier is inactive." in content
    assert "Reactivate supplier" in content
    assert "Deactivate supplier" not in content


def test_cashier_purchasing_navigation_opens_suppliers(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Direct Cashier Purchasing navigation to suppliers."""

    _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.cashier)

    response = client.get(reverse("purchasing:supplier_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Purchasing" in content
    assert 'href="/purchasing/suppliers/"' in content
    assert "Register supplier" not in content
