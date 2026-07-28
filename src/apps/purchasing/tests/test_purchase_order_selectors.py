"""Tests for purchase-order selectors."""

from decimal import Decimal

import pytest

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
)
from apps.purchasing.selectors import (
    get_purchase_order_by_id,
    get_purchase_orders_for_supplier,
    search_purchase_orders,
)
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CreatePurchaseOrderCommand,
    add_purchase_order_line,
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
            preferred_currency="UGX",
        ),
    )


def _create_product(
    *,
    context: PurchasingTestContext,
) -> Product:
    """Create one active product for selector tests."""

    category = ProductCategory(
        code="PO-SELECTOR",
        name="Purchase Order Selector Products",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="SELECTOR-PART-001",
        name="Selector Brake Pad",
        category=category,
        unit=ProductUnit.EACH,
        description="Purchase-order selector product.",
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    return product


def _create_order(
    *,
    context: PurchasingTestContext,
    supplier_id: int,
    supplier_reference: str = "",
) -> PurchaseOrder:
    """Create one purchase order for selector tests."""

    return create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier_id,
            supplier_reference=supplier_reference,
            discount_percentage=Decimal("0.00"),
            tax_percentage=Decimal("0.00"),
            delivery_cost=Decimal("0.00"),
        ),
    )


@pytest.mark.django_db
def test_search_purchase_orders_by_number_and_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Find orders by order and supplier identity."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="CASTROL-UG",
        name="Castrol Uganda",
    )
    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
        supplier_reference="CASTROL-REF-100",
    )

    assert list(search_purchase_orders(query=order.purchase_order_number)) == [order]

    assert list(search_purchase_orders(query="Castrol Uganda")) == [order]

    assert list(search_purchase_orders(query="CASTROL-REF-100")) == [order]


@pytest.mark.django_db
def test_search_purchase_orders_by_product(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Find an order through its product snapshots."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PRODUCT-SUPPLIER",
        name="Product Search Supplier",
    )
    product = _create_product(context=purchasing_context)
    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )

    add_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("2.000"),
            unit_cost=Decimal("25000.00"),
        ),
    )

    assert list(search_purchase_orders(query="Selector Brake Pad")) == [order]

    assert list(search_purchase_orders(query="SELECTOR-PART-001")) == [order]


@pytest.mark.django_db
def test_filter_purchase_orders_by_status_and_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Combine status and supplier filtering."""

    first_supplier = _create_supplier(
        context=purchasing_context,
        code="FILTER-SUPPLIER-01",
        name="First Filter Supplier",
    )
    second_supplier = _create_supplier(
        context=purchasing_context,
        code="FILTER-SUPPLIER-02",
        name="Second Filter Supplier",
    )
    product = _create_product(context=purchasing_context)

    submitted_order = _create_order(
        context=purchasing_context,
        supplier_id=first_supplier.pk,
    )
    _create_order(
        context=purchasing_context,
        supplier_id=second_supplier.pk,
    )

    add_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_id=submitted_order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("1.000"),
            unit_cost=Decimal("30000.00"),
        ),
    )
    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=submitted_order.pk,
    )

    assert list(
        search_purchase_orders(
            status=PurchaseOrderStatus.SUBMITTED,
            supplier_id=first_supplier.pk,
        )
    ) == [submitted_order]

    assert (
        list(
            search_purchase_orders(
                status=PurchaseOrderStatus.DRAFT,
                supplier_id=first_supplier.pk,
            )
        )
        == []
    )


@pytest.mark.django_db
def test_get_purchase_order_loads_lines_and_supplier(
    purchasing_context: PurchasingTestContext,
    django_assert_num_queries,
) -> None:
    """Load one order with its related display data."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="DETAIL-SUPPLIER",
        name="Detail Supplier",
    )
    product = _create_product(context=purchasing_context)
    order = _create_order(
        context=purchasing_context,
        supplier_id=supplier.pk,
    )
    line = add_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("4.000"),
            unit_cost=Decimal("20000.00"),
        ),
    )

    with django_assert_num_queries(2):
        selected = get_purchase_order_by_id(purchase_order_id=order.pk)

        assert selected.supplier == supplier
        assert list(selected.lines.all()) == [line]

    assert list(get_purchase_orders_for_supplier(supplier_id=supplier.pk)) == [order]
