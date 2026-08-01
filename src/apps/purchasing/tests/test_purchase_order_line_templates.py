"""Tests for purchase-order product-line templates."""

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

pytestmark = pytest.mark.django_db


def _create_product(
    *,
    context: PurchasingTestContext,
) -> Product:
    """Create one product for template tests."""

    category = ProductCategory(
        code="PO-LINE-TEMPLATE-CAT",
        name="Purchase Line Template Category",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="PO-LINE-TEMPLATE-001",
        name="Template Engine Filter",
        category=category,
        unit=ProductUnit.EACH,
        description="Premium engine filter.",
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
            code="PO-LINE-TEMPLATE-SUP",
            name="Purchase Line Template Supplier",
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
        ),
    )

    return supplier, purchase_order


def _create_line(
    *,
    context: PurchasingTestContext,
):
    """Create one order and product line."""

    supplier, purchase_order = _create_purchase_order(context=context)
    product = _create_product(context=context)

    line = add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("2.000"),
            unit_cost=Decimal("25000.00"),
            description_override=("Supplier engine-filter package."),
        ),
    )

    return supplier, purchase_order, product, line


def test_add_product_template_displays_fields(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display available product-line controls."""

    _supplier, purchase_order = _create_purchase_order(context=purchasing_context)
    product = _create_product(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Add product" in content
    assert product.sku in content
    assert product.name in content
    assert 'name="product"' in content
    assert 'name="quantity_ordered"' in content
    assert 'name="unit_cost"' in content
    assert 'name="description_override"' in content


def test_edit_product_template_displays_snapshot(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display immutable product and editable values."""

    _supplier, purchase_order, _product, line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_line_update",
            args=(line.pk,),
        )
    )

    content = response.content.decode()
    form = response.context["form"]

    assert response.status_code == 200
    assert "Edit product line" in content
    assert line.product_sku_snapshot in content
    assert line.product_name_snapshot in content
    assert "product" not in form.fields
    assert form.initial["quantity_ordered"] == Decimal("2.000")
    assert form.initial["unit_cost"] == Decimal("25000.00")
    assert form.initial["description_override"] == line.description_snapshot
    assert (
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
        in content
    )


def test_remove_template_displays_warning(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display line evidence before removal."""

    _supplier, purchase_order, _product, line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
    )

    content = response.content.decode()
    normalised_content = " ".join(content.split())

    assert response.status_code == 200
    assert "Remove product" in content
    assert line.product_sku_snapshot in content
    assert line.product_name_snapshot in content
    assert "2.000" in content
    assert "UGX 25000.00" in normalised_content
    assert "UGX 50000.00" in normalised_content
    assert "Keep product" in content


def test_draft_detail_displays_product_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display add, edit and remove actions to Manager."""

    _supplier, purchase_order, _product, line = _create_line(context=purchasing_context)

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
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_line_update",
            args=(line.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
        in content
    )
    assert "Add product" in content
    assert "Edit" in content
    assert "Remove" in content


def test_empty_draft_displays_add_first_product(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Offer product creation for an empty draft."""

    _supplier, purchase_order = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "No products added" in content
    assert "Add first product" in content
    assert (
        reverse(
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        )
        in content
    )


def test_receptionist_detail_hides_product_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Hide line-write controls from Receptionist."""

    _supplier, purchase_order, _product, line = _create_line(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

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
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        )
        not in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_line_update",
            args=(line.pk,),
        )
        not in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
        not in content
    )


def test_submitted_order_hides_product_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Hide line controls after draft submission."""

    _supplier, purchase_order, _product, line = _create_line(context=purchasing_context)

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
            "purchasing:purchase_order_line_add",
            args=(purchase_order.pk,),
        )
        not in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_line_update",
            args=(line.pk,),
        )
        not in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_line_remove",
            args=(line.pk,),
        )
        not in content
    )
