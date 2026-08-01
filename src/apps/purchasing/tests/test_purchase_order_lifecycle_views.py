"""Tests for purchase-order lifecycle browser views."""

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
from apps.purchasing.constants import (
    PurchaseOrderStatus,
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
    """Create one product for lifecycle tests."""

    category = ProductCategory(
        code="PO-LIFECYCLE-CAT",
        name="Purchase Order Lifecycle Category",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="PO-LIFECYCLE-001",
        name="Lifecycle Oil Filter",
        category=category,
        unit=ProductUnit.EACH,
        description="Lifecycle test product.",
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

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="PO-LIFECYCLE-SUPPLIER",
            name="Purchase Lifecycle Supplier",
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

    if with_line:
        product = _create_product(context=context)

        add_purchase_order_line(
            actor=context.manager,
            purchase_order_id=(purchase_order.pk),
            command=AddPurchaseOrderLineCommand(
                product_id=product.pk,
                quantity_ordered=Decimal("2.000"),
                unit_cost=Decimal("25000.00"),
            ),
        )

    return purchase_order


def test_purchase_order_lifecycle_urls_reverse() -> None:
    """Reverse submit, approve and cancel URLs."""

    assert reverse(
        "purchasing:purchase_order_submit",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/submit/")

    assert reverse(
        "purchasing:purchase_order_approve",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/approve/")

    assert reverse(
        "purchasing:purchase_order_cancel",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/cancel/")


def test_manager_opens_lifecycle_forms(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display all lifecycle confirmation pages."""

    purchase_order = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    for route_name in (
        "purchase_order_submit",
        "purchase_order_approve",
        "purchase_order_cancel",
    ):
        response = client.get(
            reverse(
                f"purchasing:{route_name}",
                args=(purchase_order.pk,),
            )
        )

        assert response.status_code == 200
        assert response.context["purchase_order"] == purchase_order


def test_manager_submits_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Submit a complete draft order."""

    purchase_order = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_submit",
            args=(purchase_order.pk,),
        ),
        {
            "confirmation": "on",
        },
    )

    purchase_order.refresh_from_db()

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:purchase_order_detail",
        args=(purchase_order.pk,),
    )
    assert purchase_order.status == (PurchaseOrderStatus.SUBMITTED)
    assert purchase_order.submitted_at is not None
    assert purchase_order.submitted_by == (purchasing_context.manager)


def test_empty_purchase_order_cannot_be_submitted(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject submission without any products."""

    purchase_order = _create_purchase_order(
        context=purchasing_context,
        with_line=False,
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_submit",
            args=(purchase_order.pk,),
        ),
        {
            "confirmation": "on",
        },
    )

    purchase_order.refresh_from_db()

    form = response.context["form"]

    assert response.status_code == 200
    assert purchase_order.status == (PurchaseOrderStatus.DRAFT)
    assert "Add at least one product" in " ".join(form.non_field_errors())


def test_manager_approves_submitted_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Approve a submitted purchase order."""

    purchase_order = _create_purchase_order(context=purchasing_context)

    submit_purchase_order(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_approve",
            args=(purchase_order.pk,),
        ),
        {
            "confirmation": "on",
        },
    )

    purchase_order.refresh_from_db()

    assert response.status_code == 302
    assert purchase_order.status == (PurchaseOrderStatus.APPROVED)
    assert purchase_order.approved_at is not None
    assert purchase_order.approved_by == (purchasing_context.manager)


def test_draft_purchase_order_cannot_be_approved(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject approval before submission."""

    purchase_order = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_approve",
            args=(purchase_order.pk,),
        ),
        {
            "confirmation": "on",
        },
    )

    purchase_order.refresh_from_db()
    form = response.context["form"]

    assert response.status_code == 200
    assert purchase_order.status == (PurchaseOrderStatus.DRAFT)
    assert "Only a submitted purchase order" in " ".join(form.non_field_errors())


def test_manager_cancels_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Cancel an unreceived purchase order."""

    purchase_order = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:purchase_order_cancel",
            args=(purchase_order.pk,),
        ),
        {
            "reason": ("Supplier cannot fulfil the order."),
        },
    )

    purchase_order.refresh_from_db()

    assert response.status_code == 302
    assert purchase_order.status == (PurchaseOrderStatus.CANCELLED)
    assert purchase_order.cancellation_reason == ("Supplier cannot fulfil the order.")
    assert purchase_order.cancelled_at is not None
    assert purchase_order.cancelled_by == (purchasing_context.manager)


def test_receptionist_cannot_change_order_lifecycle(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep lifecycle transitions under management."""

    purchase_order = _create_purchase_order(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    responses = (
        client.post(
            reverse(
                "purchasing:purchase_order_submit",
                args=(purchase_order.pk,),
            ),
            {
                "confirmation": "on",
            },
        ),
        client.post(
            reverse(
                "purchasing:purchase_order_approve",
                args=(purchase_order.pk,),
            ),
            {
                "confirmation": "on",
            },
        ),
        client.post(
            reverse(
                "purchasing:purchase_order_cancel",
                args=(purchase_order.pk,),
            ),
            {
                "reason": "Forbidden cancellation.",
            },
        ),
    )

    purchase_order.refresh_from_db()

    assert all(response.status_code == 403 for response in responses)
    assert purchase_order.status == (PurchaseOrderStatus.DRAFT)


def test_missing_lifecycle_purchase_order_returns_404(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return HTTP 404 for an unknown order."""

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_submit",
            args=(999999,),
        )
    )

    assert response.status_code == 404
