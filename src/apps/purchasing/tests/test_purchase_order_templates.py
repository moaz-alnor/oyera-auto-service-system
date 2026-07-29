"""Tests for purchase-order templates and navigation."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

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
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _create_supplier(
    *,
    context: PurchasingTestContext,
):
    """Create one supplier for template tests."""

    return register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="PO-TEMPLATE-SUPPLIER",
            name="Purchase Order Template Supplier",
            contact_name="Amina Musa",
            phone_number="+256700123456",
            email="purchase-orders@example.com",
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )


def _create_product(
    *,
    context: PurchasingTestContext,
) -> Product:
    """Create one active catalogue product."""

    category = ProductCategory(
        code="PO-TEMPLATE-PARTS",
        name="Purchase Order Template Parts",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="PO-TEMPLATE-001",
        name="Template Brake Pad",
        category=category,
        unit=ProductUnit.EACH,
        description="Premium brake pad set.",
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
    with_line: bool = True,
):
    """Create one draft purchase order."""

    supplier = _create_supplier(context=context)

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
            discount_percentage=Decimal("10.00"),
            tax_percentage=Decimal("18.00"),
            delivery_cost=Decimal("15000.00"),
            expected_delivery_date=(timezone.localdate() + timedelta(days=7)),
            supplier_reference="PO-TEMPLATE-REF",
            notes="Purchase-order template test.",
        ),
    )

    line = None

    if with_line:
        product = _create_product(context=context)

        line = add_purchase_order_line(
            actor=context.manager,
            purchase_order_id=purchase_order.pk,
            command=AddPurchaseOrderLineCommand(
                product_id=product.pk,
                quantity_ordered=Decimal("2.000"),
                unit_cost=Decimal("25000.00"),
                description_override=("Supplier brake pad package."),
            ),
        )

    return supplier, purchase_order, line


def test_manager_purchase_order_list_displays_actions_and_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display purchase-order data and Manager actions."""

    supplier, purchase_order, _line = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:purchase_order_list"))

    content = response.content.decode()
    normalised_content = " ".join(content.split())

    assert response.status_code == 200
    assert purchase_order.purchase_order_number in content
    assert supplier.name in content
    assert "PO-TEMPLATE-REF" in content
    assert "Draft" in content
    assert "UGX 68100.00" in normalised_content
    assert "Create purchase order" in content
    assert "Suppliers" in content
    assert "Supplier invoices" in content


def test_receptionist_purchase_order_list_is_read_only(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Hide creation controls from Receptionist."""

    _supplier, purchase_order, _line = _create_purchase_order(
        context=purchasing_context
    )

    client.force_login(purchasing_context.receptionist)

    response = client.get(reverse("purchasing:purchase_order_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert purchase_order.purchase_order_number in content
    assert "Create purchase order" not in content


def test_purchase_order_list_displays_filter_values(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display query, status and supplier filters."""

    supplier, purchase_order, _line = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:purchase_order_list"),
        {
            "q": purchase_order.supplier_reference,
            "status": "DRAFT",
            "supplier": supplier.pk,
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert f'value="{purchase_order.supplier_reference}"' in content
    assert 'value="DRAFT"' in content
    assert supplier.supplier_number in content
    assert "Clear" in content


def test_purchase_order_form_displays_header_fields(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display all purchase-order header controls."""

    supplier = _create_supplier(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:purchase_order_create"),
        {
            "supplier": supplier.pk,
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Create purchase order" in content
    assert 'name="supplier"' in content
    assert 'name="currency"' in content
    assert 'name="discount_percentage"' in content
    assert 'name="tax_percentage"' in content
    assert 'name="delivery_cost"' in content
    assert 'name="expected_delivery_date"' in content
    assert 'name="supplier_reference"' in content
    assert 'name="notes"' in content
    assert "remain in" in content
    assert "Draft" in content


def test_draft_purchase_order_detail_displays_line_and_totals(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display order details, line snapshots and totals."""

    supplier, purchase_order, line = _create_purchase_order(context=purchasing_context)

    assert line is not None

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()
    normalised_content = " ".join(content.split())

    assert response.status_code == 200
    assert purchase_order.purchase_order_number in content
    assert supplier.name in content
    assert line.product_sku_snapshot in content
    assert line.product_name_snapshot in content
    assert "2.000" in content
    assert "UGX 25000.00" in normalised_content
    assert "UGX 50000.00" in normalised_content
    assert "UGX 68100.00" in normalised_content
    assert "Edit purchase order" in content
    assert "No products added" not in content


def test_receptionist_detail_hides_edit_action(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep purchase-order editing under management."""

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
    assert purchase_order.purchase_order_number in content
    assert "Edit purchase order" not in content


def test_supplier_detail_links_purchase_order_workflow(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Link supplier records to purchase-order workflows."""

    supplier, purchase_order, _line = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_detail",
            args=(supplier.pk,),
        )
    )

    content = response.content.decode()

    purchase_order_list_url = (
        reverse("purchasing:purchase_order_list") + f"?supplier={supplier.pk}"
    )
    purchase_order_create_url = (
        reverse("purchasing:purchase_order_create") + f"?supplier={supplier.pk}"
    )
    purchase_order_detail_url = reverse(
        "purchasing:purchase_order_detail",
        args=(purchase_order.pk,),
    )

    assert response.status_code == 200
    assert purchase_order_list_url in content
    assert purchase_order_create_url in content
    assert purchase_order_detail_url in content
    assert "View all purchase orders" in content
