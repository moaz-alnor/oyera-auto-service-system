"""Tests for purchase-order lifecycle templates."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.constants import (
    PurchaseOrderStatus,
)
from apps.purchasing.models import PurchaseOrder
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CancelPurchaseOrderCommand,
    CreatePurchaseOrderCommand,
    add_purchase_order_line,
    approve_purchase_order,
    cancel_purchase_order,
    create_purchase_order,
    submit_purchase_order,
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _create_product(
    *,
    context: PurchasingTestContext,
) -> Product:
    """Create one product for lifecycle template tests."""

    category = ProductCategory(
        code="PO-LIFECYCLE-UI-CAT",
        name="Purchase Lifecycle UI Category",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="PO-LIFECYCLE-UI-001",
        name="Lifecycle Template Oil Filter",
        category=category,
        unit=ProductUnit.EACH,
        description="Lifecycle template product.",
        is_active=True,
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    return product


def _create_purchase_order(
    *,
    context: PurchasingTestContext,
):
    """Create one complete draft purchase order."""

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="PO-LIFECYCLE-UI-SUP",
            name="Purchase Lifecycle UI Supplier",
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
            discount_percentage=Decimal("10.00"),
            tax_percentage=Decimal("18.00"),
            delivery_cost=Decimal("15000.00"),
            supplier_reference="LIFECYCLE-UI-REF",
        ),
    )

    product = _create_product(context=context)

    line = add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("2.000"),
            unit_cost=Decimal("25000.00"),
        ),
    )

    return supplier, purchase_order, line


def test_submit_template_displays_confirmation_and_summary(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display draft submission evidence."""

    supplier, purchase_order, _line = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_submit",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()
    normalised_content = " ".join(content.split())

    assert response.status_code == 200
    assert "Submit purchase order" in content
    assert supplier.name in content
    assert "I confirm that the purchase order" in content
    assert 'name="confirmation"' in content
    assert "Submit for approval" in content
    assert "UGX 68100.00" in normalised_content


def test_approval_template_displays_confirmation_and_audit(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display submitted-order approval evidence."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_approve",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Approve purchase order" in content
    assert "Submitted for approval" in content
    assert "Submitted by" in content
    assert "I confirm that I reviewed" in content
    assert 'name="confirmation"' in content


def test_cancellation_template_displays_reason_control(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display cancellation warning and reason input."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Cancel purchase order" in content
    assert "Cancellation is permanent." in content
    assert "Cancellation reason" in content
    assert 'name="reason"' in content
    assert "Keep purchase order" in content


def test_draft_detail_displays_submit_and_cancel_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display draft lifecycle actions to Manager."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert (
        reverse(
            "purchasing:purchase_order_update",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_submit",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_approve",
            args=(purchase_order.pk,),
        )
        not in content
    )


def test_submitted_detail_displays_approve_and_cancel(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display submitted lifecycle actions."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert (
        reverse(
            "purchasing:purchase_order_approve",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_submit",
            args=(purchase_order.pk,),
        )
        not in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_update",
            args=(purchase_order.pk,),
        )
        not in content
    )


def test_approved_detail_displays_cancel_and_audit(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display approved status and lifecycle audit."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
    )
    approve_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Approved" in content
    assert "Submitted by" in content
    assert "Approved by" in content
    assert (
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_approve",
            args=(purchase_order.pk,),
        )
        not in content
    )


def test_cancelled_detail_hides_lifecycle_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display cancellation evidence without actions."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )
    reason = "Supplier discontinued the requested product."

    cancel_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
        command=CancelPurchaseOrderCommand(reason=reason),
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert reason in content
    assert "This purchase order was cancelled." in content

    for route_name in (
        "purchase_order_submit",
        "purchase_order_approve",
        "purchase_order_cancel",
        "purchase_order_update",
    ):
        assert (
            reverse(
                f"purchasing:{route_name}",
                args=(purchase_order.pk,),
            )
            not in content
        )


def test_receptionist_detail_hides_lifecycle_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep lifecycle actions under management."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    client.force_login(purchasing_context.receptionist)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200

    for route_name in (
        "purchase_order_submit",
        "purchase_order_approve",
        "purchase_order_cancel",
    ):
        assert (
            reverse(
                f"purchasing:{route_name}",
                args=(purchase_order.pk,),
            )
            not in content
        )


def test_received_order_cannot_display_cancellation_form(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Hide cancellation controls after goods receipt."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    PurchaseOrder.objects.filter(pk=purchase_order.pk).update(
        status=PurchaseOrderStatus.RECEIVED
    )
    purchase_order.refresh_from_db()

    client.force_login(purchasing_context.manager)

    detail_response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )
    cancel_response = client.get(
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        )
    )

    detail_content = detail_response.content.decode()
    cancel_content = cancel_response.content.decode()

    assert detail_response.status_code == 200
    assert cancel_response.status_code == 200
    assert (
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        )
        not in detail_content
    )
    assert "cannot be cancelled" in cancel_content
    assert 'name="reason"' not in cancel_content
