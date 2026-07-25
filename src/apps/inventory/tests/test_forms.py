"""Tests for inventory browser forms."""

from decimal import Decimal

import pytest
from django import forms

from apps.inventory.constants import (
    ReservationStatus,
    StockMovementType,
)
from apps.inventory.forms import (
    AdjustStockForm,
    InventoryItemForm,
    IssueStockForm,
    ReceiveStockForm,
    ReleaseReservationForm,
    ReserveStockForm,
    ReturnStockForm,
    StockLocationForm,
)
from apps.inventory.models import (
    StockLocation,
    StockMovement,
    StockReservation,
)
from apps.inventory.tests.conftest import (
    InventoryReservationContext,
    InventoryTestContext,
)


@pytest.mark.django_db
def test_location_form_normalizes_valid_code(
    inventory_context: InventoryTestContext,
) -> None:
    """Accept a code that produces a stable normalized key."""

    form = StockLocationForm(
        data={
            "code": "  shelf-a / 01  ",
            "name": "Shelf A 01",
            "description": "",
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["code"] == "shelf-a / 01"


@pytest.mark.django_db
def test_location_form_rejects_duplicate_normalized_code(
    inventory_context: InventoryTestContext,
) -> None:
    """Reject a differently formatted duplicate location code."""

    form = StockLocationForm(
        data={
            "code": " main store ",
            "name": "Duplicate Main Store",
            "description": "",
        }
    )

    assert not form.is_valid()
    assert "code" in form.errors
    assert "already exists" in form.errors["code"][0]


@pytest.mark.django_db
def test_inventory_item_form_lists_active_choices(
    inventory_context: InventoryTestContext,
) -> None:
    """List active catalogue products and stock locations."""

    inactive_location = StockLocation(
        code="OLD-STORE",
        name="Old Store",
        is_active=False,
        created_by=inventory_context.manager,
        updated_by=inventory_context.manager,
    )
    inactive_location.full_clean()
    inactive_location.save()

    form = InventoryItemForm()

    product_field = form.fields["product"]
    location_field = form.fields["location"]

    assert isinstance(
        product_field,
        forms.ModelChoiceField,
    )
    assert isinstance(
        location_field,
        forms.ModelChoiceField,
    )

    assert inventory_context.product in product_field.queryset
    assert inventory_context.location in location_field.queryset
    assert inactive_location not in location_field.queryset


@pytest.mark.django_db
def test_reservation_form_lists_matching_inventory_items(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Offer active stock records for the required product."""

    context = inventory_reservation_context

    form = ReserveStockForm(requirement=context.requirement)

    field = form.fields["inventory_item"]

    assert isinstance(field, forms.ModelChoiceField)
    assert context.inventory.inventory_item in field.queryset


@pytest.mark.django_db
def test_reservation_form_excludes_existing_active_reservation(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Hide an item already reserved for the requirement."""

    context = inventory_reservation_context

    StockReservation.objects.create(
        inventory_item=context.inventory.inventory_item,
        work_product_requirement=context.requirement,
        status=ReservationStatus.ACTIVE,
        quantity_reserved=Decimal("1.000"),
        quantity_issued=Decimal("0.000"),
        quantity_released=Decimal("0.000"),
        reserved_by=context.inventory.manager,
    )

    form = ReserveStockForm(requirement=context.requirement)

    field = form.fields["inventory_item"]

    assert isinstance(field, forms.ModelChoiceField)
    assert context.inventory.inventory_item not in field.queryset


@pytest.mark.django_db
def test_receipt_form_normalizes_currency(
    inventory_context: InventoryTestContext,
) -> None:
    """Convert a valid currency code to uppercase."""

    form = ReceiveStockForm(
        data={
            "quantity": "5.000",
            "unit_cost": "15000.00",
            "currency": " ugx ",
            "external_reference": "SUP-001",
            "occurred_at": "",
            "notes": "",
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["currency"] == "UGX"


@pytest.mark.django_db
def test_issue_form_rejects_quantity_above_reservation(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Reject an issue above the remaining reservation."""

    context = inventory_reservation_context

    reservation = StockReservation.objects.create(
        inventory_item=context.inventory.inventory_item,
        work_product_requirement=context.requirement,
        status=ReservationStatus.ACTIVE,
        quantity_reserved=Decimal("2.000"),
        quantity_issued=Decimal("0.000"),
        quantity_released=Decimal("0.000"),
        reserved_by=context.inventory.manager,
    )

    form = IssueStockForm(
        data={
            "quantity": "3.000",
            "occurred_at": "",
            "notes": "",
        },
        reservation=reservation,
    )

    assert not form.is_valid()
    assert "quantity" in form.errors
    assert "remaining on the reservation" in (form.errors["quantity"][0])


@pytest.mark.django_db
def test_return_form_rejects_quantity_above_returnable_amount(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Reject cumulative returns above the source issue."""

    context = inventory_reservation_context

    reservation = StockReservation.objects.create(
        inventory_item=context.inventory.inventory_item,
        work_product_requirement=context.requirement,
        status=ReservationStatus.PARTIALLY_ISSUED,
        quantity_reserved=Decimal("2.000"),
        quantity_issued=Decimal("2.000"),
        quantity_released=Decimal("0.000"),
        reserved_by=context.inventory.manager,
    )

    issue = StockMovement.objects.create(
        movement_number="MOV-FORM-001",
        inventory_item=context.inventory.inventory_item,
        movement_type=StockMovementType.ISSUE,
        quantity=Decimal("2.000"),
        reservation=reservation,
        created_by=context.inventory.manager,
    )

    StockMovement.objects.create(
        movement_number="MOV-FORM-002",
        inventory_item=context.inventory.inventory_item,
        movement_type=StockMovementType.RETURN,
        quantity=Decimal("0.750"),
        reservation=reservation,
        source_movement=issue,
        created_by=context.inventory.manager,
    )

    form = ReturnStockForm(
        data={
            "quantity": "1.500",
            "occurred_at": "",
            "notes": "",
        },
        source_movement=issue,
    )

    assert not form.is_valid()
    assert "quantity" in form.errors
    assert "original issue" in form.errors["quantity"][0]


@pytest.mark.django_db
def test_adjustment_form_only_lists_adjustment_types(
    inventory_context: InventoryTestContext,
) -> None:
    """Exclude receipts, issues, and returns from adjustment input."""

    form = AdjustStockForm()

    choices = {value for value, _label in form.fields["movement_type"].choices}

    assert choices == {
        StockMovementType.ADJUSTMENT_IN,
        StockMovementType.ADJUSTMENT_OUT,
    }


@pytest.mark.django_db
def test_release_form_requires_reason(
    inventory_context: InventoryTestContext,
) -> None:
    """Reject an empty reservation-release explanation."""

    form = ReleaseReservationForm(data={"reason": "   "})

    assert not form.is_valid()
    assert "reason" in form.errors
