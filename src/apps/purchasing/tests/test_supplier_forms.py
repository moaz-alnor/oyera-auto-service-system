"""Tests for supplier-management browser forms."""

import pytest
from django import forms

from apps.purchasing.forms import (
    SupplierRegistrationForm,
    SupplierUpdateForm,
)
from apps.purchasing.models import Supplier
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _valid_supplier_data() -> dict[str, str]:
    """Return valid supplier browser input."""

    return {
        "code": "AUTO-PARTS-01",
        "name": "Kampala Auto Parts",
        "contact_name": "Amina Musa",
        "phone_number": "+256700123456",
        "email": "accounts@example.com",
        "address": "Industrial Area, Kampala",
        "tax_identifier": "TIN-1001",
        "payment_terms_days": "30",
        "preferred_currency": "ugx",
        "notes": "Primary parts supplier.",
    }


def test_supplier_registration_form_is_valid() -> None:
    """Accept complete supplier information."""

    form = SupplierRegistrationForm(_valid_supplier_data())

    assert form.is_valid(), form.errors
    assert form.cleaned_data["preferred_currency"] == "UGX"


def test_supplier_form_uses_expected_widgets() -> None:
    """Use consistent application form controls."""

    form = SupplierRegistrationForm()

    assert form.fields["code"].widget.attrs["class"] == "form-control"
    assert form.fields["address"].widget.attrs["rows"] == 3
    assert str(form.fields["payment_terms_days"].widget.attrs["min"]) == "0"


def test_supplier_form_hides_duplicate_confirmation() -> None:
    """Keep duplicate confirmation as hidden state."""

    form = SupplierRegistrationForm()

    field = form.fields["confirm_duplicate"]

    assert isinstance(
        field.widget,
        forms.HiddenInput,
    )


@pytest.mark.parametrize(
    "currency",
    (
        "",
        "UG",
        "UGXA",
        "12A",
    ),
)
def test_supplier_form_rejects_invalid_currency(
    currency: str,
) -> None:
    """Reject malformed currency codes."""

    data = _valid_supplier_data()
    data["preferred_currency"] = currency

    form = SupplierRegistrationForm(data)

    assert not form.is_valid()
    assert "preferred_currency" in form.errors


def test_supplier_update_form_loads_existing_data(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Load a supplier into the update form."""

    supplier = register_supplier(
        actor=purchasing_context.manager,
        command=RegisterSupplierCommand(
            code="UPDATE-PARTS",
            name="Update Parts Uganda",
            contact_name="Sarah Nakato",
            phone_number="+256700555222",
            email="update@example.com",
            address="Kampala, Uganda",
            tax_identifier="TIN-UPDATE-01",
            payment_terms_days=45,
            preferred_currency="UGX",
            notes="Supplier update test.",
        ),
    )

    form = SupplierUpdateForm(instance=supplier)

    assert isinstance(
        form.instance,
        Supplier,
    )
    assert form.initial["code"] == ("UPDATE-PARTS")
    assert form.initial["payment_terms_days"] == 45
    assert form.initial["preferred_currency"] == "UGX"
