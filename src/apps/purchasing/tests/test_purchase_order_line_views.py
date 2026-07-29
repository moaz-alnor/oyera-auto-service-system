"""Tests for purchase-order product-line views."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.product_catalogue.constants import (
    ProductUnit,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.models import (
    PurchaseOrderLine,
)
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CreatePurchaseOrderCommand,
    add_purchase_order_line,
    create_purchase_order,
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
    sku: str = "PO-LINE-VIEW-001",
    name: str = "Purchase Line View Product",
) -> Product:
    """Create one active catalogue product."""

    category = ProductCategory(
        code=f"CAT-{sku}"[:30],
        name=f"Category for {name}",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku=sku,
        name=name,
        category=category,
        unit=ProductUnit.EACH,
        description="Product-line view test.",
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
    """Create one draft purchase order."""

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="PO-LINE-VIEW-SUPPLIER",
            name="Purchase Line View Supplier",
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )

    return create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
        ),
    )


def _create_line(
    *,
    context: PurchasingTestContext,
):
    """Create an order, product and line."""

    purchase_order = _create_purchase_order(context=context)
    product = _create_product(context=context)

    line = add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("2.000"),
            unit_cost=Decimal("25000.00"),
            description_override=("Initial supplier description."),
        ),
    )

    return purchase_order, product, line


def test_purchase_order_line_urls_reverse() -> None:
    """Reverse all product-line routes."""

    assert reverse(
        "purchasing:purchase_order_line_add",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/lines/new/")

    assert reverse(
        "purchasing:purchase_order_line_update",
        args=(1,),
    ) == ("/purchasing/purchase-order-lines/1/edit/")

    assert reverse(
        "purchasing:purchase_order_line_remove",
        args=(1,),
    ) == ("/purchasing/purchase-order-lines/1/remove/")


def test_manager_opens_add_product_form(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display products available for ordering."""

    purchase_order = _create_purchase_order(context=purchasing_context)
    product = _create_product(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        )
    )

    form = response.context["form"]

    assert response.status_code == 200
    assert list(form.fields["product"].queryset) == [product]
    assert response.context["purchase_order"] == purchase_order


def test_manager_adds_purchase_order_line(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Add one product through the browser."""

    purchase_order = _create_purchase_order(context=purchasing_context)
    product = _create_product(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        ),
        {
            "product": product.pk,
            "quantity_ordered": "3.000",
            "unit_cost": "20000.00",
            "description_override": ("Browser-added product line."),
        },
    )

    line = PurchaseOrderLine.objects.get(purchase_order=purchase_order)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:purchase_order_detail",
        args=(purchase_order.pk,),
    )
    assert line.product == product
    assert line.quantity_ordered == Decimal("3.000")
    assert line.unit_cost == Decimal("20000.00")


def test_existing_product_cannot_be_added_twice(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a product already present on the order."""

    purchase_order, product, _line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        ),
        {
            "product": product.pk,
            "quantity_ordered": "1.000",
            "unit_cost": "10000.00",
            "description_override": "",
        },
    )

    assert response.status_code == 200
    assert "product" in response.context["form"].errors
    assert PurchaseOrderLine.objects.filter(purchase_order=purchase_order).count() == 1


def test_manager_updates_purchase_order_line(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Update quantity, cost and description."""

    purchase_order, _product, line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_line_update",
            args=(line.pk,),
        ),
        {
            "quantity_ordered": "4.000",
            "unit_cost": "30000.00",
            "description_override": ("Updated browser description."),
        },
    )

    line.refresh_from_db()

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:purchase_order_detail",
        args=(purchase_order.pk,),
    )
    assert line.quantity_ordered == Decimal("4.000")
    assert line.unit_cost == Decimal("30000.00")
    assert line.description_snapshot == ("Updated browser description.")


def test_manager_removes_purchase_order_line(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Remove a product from a draft order."""

    purchase_order, _product, line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    confirmation_response = client.get(
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
    )

    response = client.post(
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
    )

    assert confirmation_response.status_code == 200
    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:purchase_order_detail",
        args=(purchase_order.pk,),
    )
    assert not PurchaseOrderLine.objects.filter(pk=line.pk).exists()


def test_receptionist_cannot_add_product_line(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep product-line changes under management."""

    purchase_order = _create_purchase_order(context=purchasing_context)
    product = _create_product(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    response = client.post(
        reverse(
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        ),
        {
            "product": product.pk,
            "quantity_ordered": "1.000",
            "unit_cost": "10000.00",
            "description_override": "",
        },
    )

    assert response.status_code == 403
    assert not PurchaseOrderLine.objects.exists()


def test_receptionist_cannot_update_or_remove_line(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep line editing and removal under management."""

    _purchase_order, _product, line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    update_response = client.post(
        reverse(
            "purchasing:purchase_order_line_update",
            args=(line.pk,),
        ),
        {
            "quantity_ordered": "9.000",
            "unit_cost": "90000.00",
            "description_override": "",
        },
    )

    remove_response = client.post(
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
    )

    line.refresh_from_db()

    assert update_response.status_code == 403
    assert remove_response.status_code == 403
    assert line.quantity_ordered == Decimal("2.000")


def test_missing_purchase_order_line_returns_404(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return HTTP 404 for an unknown line."""

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_line_update",
            args=(999999,),
        )
    )

    assert response.status_code == 404
