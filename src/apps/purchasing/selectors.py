"""Read-only queries for supplier purchasing."""

from decimal import Decimal

from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Prefetch,
    Q,
    QuerySet,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.inventory.models import StockMovement
from apps.purchasing.constants import (
    SupplierInvoiceStatus,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierPayment,
)
from apps.purchasing.normalization import (
    normalize_supplier_code,
    normalize_supplier_name,
)


def search_suppliers(
    *,
    query: str = "",
    include_inactive: bool = False,
) -> QuerySet[Supplier]:
    """Return suppliers matching general search text."""

    suppliers = Supplier.objects.select_related(
        "created_by",
        "updated_by",
    )

    if not include_inactive:
        suppliers = suppliers.filter(is_active=True)

    search_value = query.strip()

    if not search_value:
        return suppliers

    normalized_code = normalize_supplier_code(search_value)
    normalized_name = normalize_supplier_name(search_value)

    search_filter = (
        Q(supplier_number__icontains=search_value)
        | Q(code__icontains=search_value)
        | Q(name__icontains=search_value)
        | Q(contact_name__icontains=search_value)
        | Q(phone_number__icontains=search_value)
        | Q(email__icontains=search_value)
        | Q(tax_identifier__icontains=search_value)
    )

    if normalized_code:
        search_filter |= Q(normalized_code__icontains=normalized_code)

    if normalized_name:
        search_filter |= Q(normalized_name__icontains=normalized_name)

    return suppliers.filter(search_filter).distinct()


def find_possible_supplier_duplicates(
    *,
    code: str,
    name: str,
    phone_number: str = "",
    email: str = "",
    tax_identifier: str = "",
    exclude_supplier_id: int | None = None,
) -> QuerySet[Supplier]:
    """Return records that may represent one supplier."""

    normalized_code = normalize_supplier_code(code)
    normalized_name = normalize_supplier_name(name)

    duplicate_filter = Q(normalized_code=normalized_code) | Q(
        normalized_name=normalized_name
    )

    phone_value = phone_number.strip()
    email_value = email.strip().casefold()
    tax_value = tax_identifier.strip().upper()

    if phone_value:
        duplicate_filter |= Q(phone_number__iexact=phone_value)

    if email_value:
        duplicate_filter |= Q(email__iexact=email_value)

    if tax_value:
        duplicate_filter |= Q(tax_identifier__iexact=tax_value)

    suppliers = Supplier.objects.filter(duplicate_filter)

    if exclude_supplier_id is not None:
        suppliers = suppliers.exclude(pk=exclude_supplier_id)

    return (
        suppliers.select_related(
            "created_by",
            "updated_by",
        )
        .order_by(
            "-is_active",
            "name",
            "supplier_number",
        )
        .distinct()
    )


def get_supplier_by_id(
    *,
    supplier_id: int,
) -> Supplier:
    """Return one supplier by primary key."""

    return Supplier.objects.select_related(
        "created_by",
        "updated_by",
    ).get(pk=supplier_id)


def purchase_order_list_queryset() -> QuerySet[PurchaseOrder]:
    """Return orders with display relationships loaded."""

    order_lines = (
        PurchaseOrderLine.objects.select_related(
            "product",
            "created_by",
            "updated_by",
        )
        .all()
        .order_by(
            "position",
            "pk",
        )
    )

    return (
        PurchaseOrder.objects.select_related(
            "supplier",
            "created_by",
            "updated_by",
            "submitted_by",
            "approved_by",
            "cancelled_by",
        )
        .prefetch_related(
            Prefetch(
                "lines",
                queryset=order_lines,
            )
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def search_purchase_orders(
    *,
    query: str = "",
    status: str = "",
    supplier_id: int | None = None,
) -> QuerySet[PurchaseOrder]:
    """Return purchase orders matching supplied filters."""

    purchase_orders = purchase_order_list_queryset()

    if status:
        purchase_orders = purchase_orders.filter(status=status)

    if supplier_id is not None:
        purchase_orders = purchase_orders.filter(supplier_id=supplier_id)

    search_value = query.strip()

    if not search_value:
        return purchase_orders

    return purchase_orders.filter(
        Q(purchase_order_number__icontains=(search_value))
        | Q(supplier_number_snapshot__icontains=(search_value))
        | Q(supplier_code_snapshot__icontains=(search_value))
        | Q(supplier_name_snapshot__icontains=(search_value))
        | Q(supplier_reference__icontains=(search_value))
        | Q(lines__product_sku_snapshot__icontains=(search_value))
        | Q(lines__product_name_snapshot__icontains=(search_value))
    ).distinct()


def get_purchase_order_by_id(
    *,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Return one purchase order and its lines."""

    return purchase_order_list_queryset().get(pk=purchase_order_id)


def get_purchase_orders_for_supplier(
    *,
    supplier_id: int,
) -> QuerySet[PurchaseOrder]:
    """Return all orders belonging to one supplier."""

    return purchase_order_list_queryset().filter(supplier_id=supplier_id)


def goods_receipt_list_queryset() -> QuerySet[GoodsReceipt]:
    """Return receipts with their audit relationships loaded."""

    receipt_lines = (
        GoodsReceiptLine.objects.select_related(
            "purchase_order_line",
            "purchase_order_line__product",
            "inventory_item",
            "inventory_item__product",
            "inventory_item__location",
            "stock_movement",
            "stock_movement__created_by",
            "created_by",
        )
        .all()
        .order_by(
            "purchase_order_line__position",
            "pk",
        )
    )

    return (
        GoodsReceipt.objects.select_related(
            "purchase_order",
            "purchase_order__supplier",
            "received_by",
        )
        .prefetch_related(
            Prefetch(
                "lines",
                queryset=receipt_lines,
            )
        )
        .order_by(
            "-received_at",
            "-pk",
        )
    )


def search_goods_receipts(
    *,
    query: str = "",
    purchase_order_id: int | None = None,
    supplier_id: int | None = None,
) -> QuerySet[GoodsReceipt]:
    """Return goods receipts matching supplied filters."""

    receipts = goods_receipt_list_queryset()

    if purchase_order_id is not None:
        receipts = receipts.filter(purchase_order_id=purchase_order_id)

    if supplier_id is not None:
        receipts = receipts.filter(purchase_order__supplier_id=supplier_id)

    search_value = query.strip()

    if not search_value:
        return receipts

    return receipts.filter(
        Q(goods_receipt_number__icontains=(search_value))
        | Q(purchase_order_number_snapshot__icontains=(search_value))
        | Q(supplier_number_snapshot__icontains=(search_value))
        | Q(supplier_name_snapshot__icontains=(search_value))
        | Q(supplier_delivery_reference__icontains=(search_value))
        | Q(lines__product_sku_snapshot__icontains=(search_value))
        | Q(lines__product_name_snapshot__icontains=(search_value))
        | Q(lines__stock_movement__movement_number__icontains=(search_value))
        | Q(lines__inventory_item__location__code__icontains=(search_value))
    ).distinct()


def get_goods_receipt_by_id(
    *,
    goods_receipt_id: int,
) -> GoodsReceipt:
    """Return one receipt with its complete audit trail."""

    return goods_receipt_list_queryset().get(pk=goods_receipt_id)


def get_goods_receipts_for_purchase_order(
    *,
    purchase_order_id: int,
) -> QuerySet[GoodsReceipt]:
    """Return all deliveries for one purchase order."""

    return goods_receipt_list_queryset().filter(purchase_order_id=purchase_order_id)


def get_goods_receipt_movements(
    *,
    goods_receipt_id: int,
) -> QuerySet[StockMovement]:
    """Return Inventory movements created by one receipt."""

    return (
        StockMovement.objects.filter(
            goods_receipt_line__goods_receipt_id=(goods_receipt_id)
        )
        .select_related(
            "inventory_item",
            "inventory_item__product",
            "inventory_item__location",
            "created_by",
        )
        .order_by(
            "occurred_at",
            "pk",
        )
    )


def supplier_invoice_list_queryset() -> QuerySet[SupplierInvoice]:
    """Return supplier invoices with financial details loaded."""

    invoice_lines = (
        SupplierInvoiceLine.objects.select_related(
            "purchase_order_line",
            "purchase_order_line__product",
            "goods_receipt_line",
            "goods_receipt_line__goods_receipt",
            "goods_receipt_line__inventory_item",
            "goods_receipt_line__inventory_item__location",
            "created_by",
        )
        .all()
        .order_by(
            "purchase_order_line__position",
            "pk",
        )
    )

    payments = (
        SupplierPayment.objects.select_related(
            "recorded_by",
            "voided_by",
        )
        .all()
        .order_by(
            "-paid_at",
            "-pk",
        )
    )

    posted_payment_total = Coalesce(
        Sum(
            "payments__amount",
            filter=Q(payments__status=(SupplierPaymentStatus.POSTED)),
        ),
        Value(Decimal("0.00")),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2,
        ),
    )

    return (
        SupplierInvoice.objects.select_related(
            "supplier",
            "purchase_order",
            "created_by",
            "updated_by",
            "posted_by",
            "voided_by",
        )
        .annotate(
            paid_amount=posted_payment_total,
        )
        .annotate(
            outstanding_amount=ExpressionWrapper(
                F("total") - F("paid_amount"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        )
        .prefetch_related(
            Prefetch(
                "lines",
                queryset=invoice_lines,
            ),
            Prefetch(
                "payments",
                queryset=payments,
            ),
        )
        .order_by(
            "-invoice_date",
            "-pk",
        )
    )


def search_supplier_invoices(
    *,
    query: str = "",
    status: str = "",
    supplier_id: int | None = None,
    purchase_order_id: int | None = None,
    overdue_only: bool = False,
) -> QuerySet[SupplierInvoice]:
    """Return supplier invoices matching supplied filters."""

    invoices = supplier_invoice_list_queryset()

    if status:
        invoices = invoices.filter(status=status)

    if supplier_id is not None:
        invoices = invoices.filter(supplier_id=supplier_id)

    if purchase_order_id is not None:
        invoices = invoices.filter(purchase_order_id=purchase_order_id)

    if overdue_only:
        invoices = invoices.filter(
            due_date__lt=timezone.localdate(),
            status__in=(
                SupplierInvoiceStatus.POSTED,
                SupplierInvoiceStatus.PARTIALLY_PAID,
            ),
        )

    search_value = query.strip()

    if not search_value:
        return invoices

    return invoices.filter(
        Q(supplier_invoice_number__icontains=(search_value))
        | Q(supplier_reference__icontains=(search_value))
        | Q(purchase_order_number_snapshot__icontains=(search_value))
        | Q(supplier_number_snapshot__icontains=(search_value))
        | Q(supplier_name_snapshot__icontains=(search_value))
        | Q(lines__product_sku_snapshot__icontains=(search_value))
        | Q(lines__product_name_snapshot__icontains=(search_value))
        | Q(
            **{
                (
                    "lines__goods_receipt_line__"
                    "goods_receipt__"
                    "goods_receipt_number__icontains"
                ): search_value
            }
        )
        | Q(payments__payment_number__icontains=(search_value))
        | Q(payments__external_reference__icontains=(search_value))
    ).distinct()


def get_supplier_invoice_by_id(
    *,
    supplier_invoice_id: int,
) -> SupplierInvoice:
    """Return one invoice with lines and payments."""

    return supplier_invoice_list_queryset().get(pk=supplier_invoice_id)


def get_supplier_invoices_for_supplier(
    *,
    supplier_id: int,
) -> QuerySet[SupplierInvoice]:
    """Return all invoices belonging to one supplier."""

    return supplier_invoice_list_queryset().filter(supplier_id=supplier_id)


def get_supplier_invoices_for_purchase_order(
    *,
    purchase_order_id: int,
) -> QuerySet[SupplierInvoice]:
    """Return all invoices for one purchase order."""

    return supplier_invoice_list_queryset().filter(purchase_order_id=purchase_order_id)


def supplier_payment_list_queryset() -> QuerySet[SupplierPayment]:
    """Return supplier payments with relationships loaded."""

    return SupplierPayment.objects.select_related(
        "supplier_invoice",
        "supplier_invoice__supplier",
        "supplier_invoice__purchase_order",
        "recorded_by",
        "voided_by",
    ).order_by(
        "-paid_at",
        "-pk",
    )


def search_supplier_payments(
    *,
    query: str = "",
    status: str = "",
    method: str = "",
    supplier_invoice_id: int | None = None,
    supplier_id: int | None = None,
) -> QuerySet[SupplierPayment]:
    """Return supplier payments matching supplied filters."""

    payments = supplier_payment_list_queryset()

    if status:
        payments = payments.filter(status=status)

    if method:
        payments = payments.filter(method=method)

    if supplier_invoice_id is not None:
        payments = payments.filter(supplier_invoice_id=supplier_invoice_id)

    if supplier_id is not None:
        payments = payments.filter(supplier_invoice__supplier_id=supplier_id)

    search_value = query.strip()

    if not search_value:
        return payments

    return payments.filter(
        Q(payment_number__icontains=search_value)
        | Q(external_reference__icontains=(search_value))
        | Q(**{("supplier_invoice__supplier_invoice_number__icontains"): search_value})
        | Q(**{("supplier_invoice__supplier_reference__icontains"): search_value})
        | Q(**{("supplier_invoice__supplier_number_snapshot__icontains"): search_value})
        | Q(**{("supplier_invoice__supplier_name_snapshot__icontains"): search_value})
    ).distinct()


def get_supplier_payment_by_id(
    *,
    supplier_payment_id: int,
) -> SupplierPayment:
    """Return one supplier payment by primary key."""

    return supplier_payment_list_queryset().get(pk=supplier_payment_id)
