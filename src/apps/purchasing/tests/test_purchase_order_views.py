"""Tests for purchase-order browser views."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.purchasing.constants import (
    PurchaseOrderStatus,
)
from apps.purchasing.models import (
    PurchaseOrder,
    Supplier,
)
from apps.purchasing.services.purchase_orders import (
    CreatePurchaseOrderCommand,
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
    code: str,
    name: str,
) -> Supplier:
    """Create one supplier for view tests."""

    return register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code=code,
            name=name,
            contact_name="Amina Musa",
            phone_number="+256700123456",
            email=(f"{code.lower()}@example.com"),
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )


def _create_purchase_order(
    *,
    context: PurchasingTestContext,
    supplier: Supplier,
    supplier_reference: str,
) -> PurchaseOrder:
    """Create one draft purchase order."""

    return create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
            discount_percentage=Decimal("5.00"),
            tax_percentage=Decimal("18.00"),
            delivery_cost=Decimal("15000.00"),
            expected_delivery_date=(timezone.localdate() + timedelta(days=7)),
            supplier_reference=(supplier_reference),
            notes="Purchase-order view test.",
        ),
    )


def _valid_order_data(
    *,
    supplier_id: int,
    reference: str,
) -> dict[str, str]:
    """Return valid purchase-order form data."""

    return {
        "supplier": str(supplier_id),
        "currency": "ugx",
        "discount_percentage": "5.00",
        "tax_percentage": "18.00",
        "delivery_cost": "15000.00",
        "expected_delivery_date": (
            timezone.localdate() + timedelta(days=7)
        ).isoformat(),
        "supplier_reference": reference,
        "notes": "Browser purchase order.",
    }


def test_purchase_order_urls_reverse() -> None:
    """Reverse all basic purchase-order routes."""

    assert reverse("purchasing:purchase_order_list") == "/purchasing/purchase-orders/"

    assert reverse("purchasing:purchase_order_create") == (
        "/purchasing/purchase-orders/new/"
    )

    assert reverse(
        "purchasing:purchase_order_detail",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/")

    assert reverse(
        "purchasing:purchase_order_update",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/edit/")


def test_anonymous_user_is_redirected_from_purchase_orders(
    client: Client,
) -> None:
    """Require authentication for purchase orders."""

    response = client.get(reverse("purchasing:purchase_order_list"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


def test_receptionist_can_view_purchase_orders(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Allow Receptionist read-only order access."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-VIEW-SUPPLIER",
        name="Purchase View Supplier",
    )
    purchase_order = _create_purchase_order(
        context=purchasing_context,
        supplier=supplier,
        supplier_reference="VIEW-PO-001",
    )

    client.force_login(purchasing_context.receptionist)

    list_response = client.get(reverse("purchasing:purchase_order_list"))
    detail_response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert list(list_response.context["purchase_orders"]) == [purchase_order]
    assert detail_response.context["purchase_order"] == purchase_order
    assert detail_response.context["totals"].total == Decimal("15000.00")


def test_manager_creates_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Create a draft order through the browser."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-CREATE-SUPPLIER",
        name="Purchase Create Supplier",
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse("purchasing:purchase_order_create"),
        _valid_order_data(
            supplier_id=supplier.pk,
            reference="CREATE-PO-001",
        ),
    )

    purchase_order = PurchaseOrder.objects.get(supplier_reference="CREATE-PO-001")

    assert response.status_code == 302
    assert response.headers["Location"] == (
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )
    assert purchase_order.status == (PurchaseOrderStatus.DRAFT)
    assert purchase_order.currency == "UGX"
    assert purchase_order.purchase_order_number == f"PO-{purchase_order.pk:06d}"


def test_purchase_order_list_applies_filters(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Apply query, supplier, and status filters."""

    first_supplier = _create_supplier(
        context=purchasing_context,
        code="PO-FILTER-FIRST",
        name="First Filter Supplier",
    )
    second_supplier = _create_supplier(
        context=purchasing_context,
        code="PO-FILTER-SECOND",
        name="Second Filter Supplier",
    )
    first_order = _create_purchase_order(
        context=purchasing_context,
        supplier=first_supplier,
        supplier_reference="FILTER-ORDER-ONE",
    )
    _create_purchase_order(
        context=purchasing_context,
        supplier=second_supplier,
        supplier_reference="FILTER-ORDER-TWO",
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:purchase_order_list"),
        {
            "q": "FILTER-ORDER-ONE",
            "status": PurchaseOrderStatus.DRAFT,
            "supplier": first_supplier.pk,
        },
    )

    assert response.status_code == 200
    assert list(response.context["purchase_orders"]) == [first_order]
    assert response.context["selected_status"] == PurchaseOrderStatus.DRAFT
    assert response.context["selected_supplier_id"] == first_supplier.pk


def test_invalid_purchase_order_status_is_ignored(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Ignore unrecognised lifecycle filters."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-INVALID-STATUS",
        name="Invalid Status Supplier",
    )
    purchase_order = _create_purchase_order(
        context=purchasing_context,
        supplier=supplier,
        supplier_reference="INVALID-STATUS-PO",
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:purchase_order_list"),
        {
            "status": "NOT-A-STATUS",
        },
    )

    assert response.status_code == 200
    assert response.context["selected_status"] == ""
    assert list(response.context["purchase_orders"]) == [purchase_order]


def test_create_form_prefills_selected_supplier(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Preselect a supplier from its detail page."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-PREFILL-SUPPLIER",
        name="Prefill Purchase Supplier",
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:purchase_order_create"),
        {
            "supplier": supplier.pk,
        },
    )

    form = response.context["form"]

    assert response.status_code == 200
    assert form.initial["supplier"] == (supplier)
    assert form.initial["currency"] == (supplier.preferred_currency)


def test_manager_updates_draft_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Update the editable order header."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-UPDATE-SUPPLIER",
        name="Purchase Update Supplier",
    )
    purchase_order = _create_purchase_order(
        context=purchasing_context,
        supplier=supplier,
        supplier_reference="ORIGINAL-PO-REF",
    )

    client.force_login(purchasing_context.manager)

    data = _valid_order_data(
        supplier_id=supplier.pk,
        reference="UPDATED-PO-REF",
    )
    data["discount_percentage"] = "10.00"
    data["delivery_cost"] = "25000.00"

    response = client.post(
        reverse(
            "purchasing:purchase_order_update",
            args=(purchase_order.pk,),
        ),
        data,
    )

    purchase_order.refresh_from_db()

    assert response.status_code == 302
    assert purchase_order.supplier_reference == ("UPDATED-PO-REF")
    assert purchase_order.discount_percentage == (Decimal("10.00"))
    assert purchase_order.delivery_cost == (Decimal("25000.00"))


def test_receptionist_cannot_create_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep order creation under management."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-FORBIDDEN-CREATE",
        name="Forbidden Create Supplier",
    )

    client.force_login(purchasing_context.receptionist)

    response = client.post(
        reverse("purchasing:purchase_order_create"),
        _valid_order_data(
            supplier_id=supplier.pk,
            reference="FORBIDDEN-CREATE-PO",
        ),
    )

    assert response.status_code == 403
    assert not PurchaseOrder.objects.filter(
        supplier_reference=("FORBIDDEN-CREATE-PO")
    ).exists()


def test_receptionist_cannot_update_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep order updates under management."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-FORBIDDEN-UPDATE",
        name="Forbidden Update Supplier",
    )
    purchase_order = _create_purchase_order(
        context=purchasing_context,
        supplier=supplier,
        supplier_reference="UNCHANGED-PO-REF",
    )

    client.force_login(purchasing_context.receptionist)

    response = client.post(
        reverse(
            "purchasing:purchase_order_update",
            args=(purchase_order.pk,),
        ),
        _valid_order_data(
            supplier_id=supplier.pk,
            reference="FORBIDDEN-UPDATE-PO",
        ),
    )

    purchase_order.refresh_from_db()

    assert response.status_code == 403
    assert purchase_order.supplier_reference == ("UNCHANGED-PO-REF")


def test_missing_purchase_order_returns_404(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return HTTP 404 for an unknown order."""

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(999999,),
        )
    )

    assert response.status_code == 404
