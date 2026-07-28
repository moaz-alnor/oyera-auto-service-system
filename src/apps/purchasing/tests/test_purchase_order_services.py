"""Tests for purchase-order application services."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.product_catalogue.constants import (
    ProductUnit,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.constants import (
    PurchaseOrderStatus,
)
from apps.purchasing.models import (
    PurchaseOrder,
    PurchaseOrderLine,
)
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CancelPurchaseOrderCommand,
    CreatePurchaseOrderCommand,
    UpdatePurchaseOrderCommand,
    UpdatePurchaseOrderLineCommand,
    add_purchase_order_line,
    approve_purchase_order,
    cancel_purchase_order,
    create_purchase_order,
    remove_purchase_order_line,
    submit_purchase_order,
    update_purchase_order,
    update_purchase_order_line,
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    deactivate_supplier,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


@pytest.fixture
def supplier(
    purchasing_context: PurchasingTestContext,
):
    """Create an active supplier for order tests."""

    return register_supplier(
        actor=purchasing_context.manager,
        command=RegisterSupplierCommand(
            code="SERVICE-SUPPLIER",
            name="Purchase Service Supplier",
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )


@pytest.fixture
def product(
    purchasing_context: PurchasingTestContext,
) -> Product:
    """Create an active catalogue product."""

    category = ProductCategory(
        code="PURCHASE-SERVICE",
        name="Purchase Service Products",
        created_by=purchasing_context.manager,
        updated_by=purchasing_context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="PURCHASE-PART-001",
        name="Purchase Service Part",
        category=category,
        unit=ProductUnit.EACH,
        description="Standard purchase test product.",
        created_by=purchasing_context.manager,
        updated_by=purchasing_context.manager,
    )
    product.full_clean()
    product.save()

    return product


def _create_order(
    *,
    context: PurchasingTestContext,
    supplier_id: int,
) -> PurchaseOrder:
    """Create one draft order through the service."""

    return create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier_id,
            discount_percentage=Decimal("0.00"),
            tax_percentage=Decimal("0.00"),
            delivery_cost=Decimal("0.00"),
            notes="Purchase-order service test.",
        ),
    )


def _add_line(
    *,
    context: PurchasingTestContext,
    order: PurchaseOrder,
    product: Product,
) -> PurchaseOrderLine:
    """Add one standard product line."""

    return add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("2.000"),
            unit_cost=Decimal("25000.00"),
        ),
    )


@pytest.mark.django_db
def test_manager_creates_purchase_order(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Create a numbered draft with supplier snapshots."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    assert order.purchase_order_number == "PO-000001"
    assert order.status == PurchaseOrderStatus.DRAFT
    assert order.currency == "UGX"
    assert order.supplier_code_snapshot == supplier.code
    assert order.supplier_name_snapshot == supplier.name


@pytest.mark.django_db
def test_receptionist_cannot_create_purchase_order(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Reject purchase-order creation without permission."""

    with pytest.raises(PermissionDenied):
        create_purchase_order(
            actor=purchasing_context.receptionist,
            command=CreatePurchaseOrderCommand(supplier_id=supplier.pk),
        )


@pytest.mark.django_db
def test_inactive_supplier_cannot_receive_order(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Reject new orders for inactive suppliers."""

    deactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=supplier.pk,
    )

    with pytest.raises(ValidationError) as exc_info:
        _create_order(
            context=purchasing_context,
            supplier_id=supplier.pk,
        )

    assert "supplier" in exc_info.value.message_dict


@pytest.mark.django_db
def test_manager_updates_draft_header(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Update financial and delivery details."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    order = update_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
        command=UpdatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="usd",
            discount_percentage=Decimal("5.00"),
            tax_percentage=Decimal("18.00"),
            delivery_cost=Decimal("5000.00"),
            supplier_reference="SUP-REF-100",
            notes="Updated purchase order.",
        ),
    )

    assert order.currency == "USD"
    assert order.discount_percentage == Decimal("5.00")
    assert order.tax_percentage == Decimal("18.00")
    assert order.delivery_cost == Decimal("5000.00")
    assert order.supplier_reference == "SUP-REF-100"


@pytest.mark.django_db
def test_manager_adds_product_line(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Add product snapshots and supplier cost."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    line = _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )

    assert line.position == 1
    assert line.product_sku_snapshot == product.sku
    assert line.product_name_snapshot == product.name
    assert line.quantity_ordered == Decimal("2.000")
    assert line.line_total == Decimal("50000.00")


@pytest.mark.django_db
def test_duplicate_product_line_is_rejected(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Allow one line per product on each order."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )

    with pytest.raises(ValidationError) as exc_info:
        _add_line(
            context=purchasing_context,
            order=order,
            product=product,
        )

    assert "product" in exc_info.value.message_dict


@pytest.mark.django_db
def test_manager_updates_purchase_order_line(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Update quantity, cost and description."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    line = _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )

    line = update_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_line_id=line.pk,
        command=UpdatePurchaseOrderLineCommand(
            quantity_ordered=Decimal("3.000"),
            unit_cost=Decimal("22000.00"),
            description_override=("Updated supplier specification."),
        ),
    )

    assert line.quantity_ordered == Decimal("3.000")
    assert line.unit_cost == Decimal("22000.00")
    assert line.line_total == Decimal("66000.00")
    assert line.description_snapshot == ("Updated supplier specification.")


@pytest.mark.django_db
def test_manager_removes_draft_line(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Remove a product before order submission."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    line = _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )

    remove_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_line_id=line.pk,
    )

    assert not PurchaseOrderLine.objects.filter(pk=line.pk).exists()


@pytest.mark.django_db
def test_empty_order_cannot_be_submitted(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Require at least one product line."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    with pytest.raises(ValidationError) as exc_info:
        submit_purchase_order(
            actor=purchasing_context.manager,
            purchase_order_id=order.pk,
        )

    assert "purchase_order" in (exc_info.value.message_dict)


@pytest.mark.django_db
def test_manager_submits_complete_order(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Submit a complete draft for approval."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )

    order = submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
    )

    assert order.status == PurchaseOrderStatus.SUBMITTED
    assert order.submitted_at is not None
    assert order.submitted_by == (purchasing_context.manager)


@pytest.mark.django_db
def test_submitted_order_cannot_be_edited(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Freeze header and lines after submission."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    line = _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )
    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
    )

    with pytest.raises(ValidationError):
        update_purchase_order_line(
            actor=purchasing_context.manager,
            purchase_order_line_id=line.pk,
            command=UpdatePurchaseOrderLineCommand(
                quantity_ordered=Decimal("4.000"),
                unit_cost=Decimal("20000.00"),
            ),
        )


@pytest.mark.django_db
def test_manager_approves_submitted_order(
    purchasing_context: PurchasingTestContext,
    supplier,
    product: Product,
) -> None:
    """Approve an order after submission."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    _add_line(
        context=purchasing_context,
        order=order,
        product=product,
    )
    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
    )

    order = approve_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
    )

    assert order.status == PurchaseOrderStatus.APPROVED
    assert order.approved_at is not None
    assert order.approved_by == (purchasing_context.manager)


@pytest.mark.django_db
def test_draft_order_cannot_be_approved(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Require submission before approval."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    with pytest.raises(ValidationError) as exc_info:
        approve_purchase_order(
            actor=purchasing_context.manager,
            purchase_order_id=order.pk,
        )

    assert "purchase_order" in (exc_info.value.message_dict)


@pytest.mark.django_db
def test_manager_cancels_purchase_order(
    purchasing_context: PurchasingTestContext,
    supplier,
) -> None:
    """Preserve cancellation actor, time and reason."""

    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    order = cancel_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
        command=CancelPurchaseOrderCommand(
            reason="  Supplier could not meet delivery.  "
        ),
    )

    assert order.status == PurchaseOrderStatus.CANCELLED
    assert order.cancelled_at is not None
    assert order.cancelled_by == (purchasing_context.manager)
    assert order.cancellation_reason == ("Supplier could not meet delivery.")
