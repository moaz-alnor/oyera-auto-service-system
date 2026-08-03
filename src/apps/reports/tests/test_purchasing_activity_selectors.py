"""Tests for Purchasing activity report selectors."""

from datetime import (
    datetime,
    time,
    timedelta,
)
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.purchasing.models import (
    GoodsReceipt,
    PurchaseOrder,
    SupplierInvoice,
    SupplierPayment,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.supplier_finance_factory import (
    create_supplier_finance_context,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.purchasing_activity import (
    PurchasingActivitySummary,
    get_purchasing_activity_report,
)


def _event_time(
    *,
    days_ago: int = 1,
) -> datetime:
    """Return a deterministic local report time."""

    report_date = timezone.localdate() - timedelta(days=days_ago)

    return timezone.make_aware(
        datetime.combine(
            report_date,
            time(
                hour=10,
                minute=0,
            ),
        ),
        timezone.get_current_timezone(),
    )


def _align_activity_times(
    *,
    supplier_invoice_id: int,
    event_time: datetime,
) -> None:
    """Place supplier-finance activity in one period."""

    supplier_invoice = SupplierInvoice.objects.get(pk=supplier_invoice_id)
    purchase_order = supplier_invoice.purchase_order

    PurchaseOrder.objects.filter(pk=purchase_order.pk).update(
        created_at=event_time,
        submitted_at=(event_time + timedelta(hours=1)),
        approved_at=(event_time + timedelta(hours=2)),
    )

    GoodsReceipt.objects.filter(purchase_order=purchase_order).update(
        received_at=(event_time + timedelta(hours=3))
    )

    SupplierInvoice.objects.filter(pk=supplier_invoice.pk).update(
        invoice_date=event_time.date(),
        posted_at=(event_time + timedelta(hours=4)),
    )

    SupplierPayment.objects.filter(supplier_invoice=supplier_invoice).update(
        paid_at=(event_time + timedelta(hours=5))
    )


@pytest.mark.django_db
def test_purchasing_report_calculates_activity(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Calculate period activity and current liability."""

    event_time = _event_time()
    report_date = event_time.date()
    today = timezone.localdate()

    context = create_supplier_finance_context(
        context=purchasing_context,
        invoice_date=report_date,
        due_date=report_date,
        payment_amount=Decimal("40000.00"),
    )

    _align_activity_times(
        supplier_invoice_id=(context.supplier_invoice.pk),
        event_time=event_time,
    )

    purchase_order = PurchaseOrder.objects.get(
        pk=(context.receipt_context.purchase_order.pk)
    )
    goods_receipt = GoodsReceipt.objects.get(
        pk=(context.receipt_context.goods_receipt.pk)
    )
    supplier_invoice = SupplierInvoice.objects.get(pk=context.supplier_invoice.pk)
    supplier_payment = SupplierPayment.objects.get(pk=context.supplier_payment.pk)

    report = get_purchasing_activity_report(
        date_range=ReportDateRange(
            start_date=report_date,
            end_date=report_date,
        ),
        as_of_date=today,
    )

    assert report.summary == (
        PurchasingActivitySummary(
            currency="UGX",
            purchase_orders_created_count=1,
            purchase_orders_submitted_count=1,
            purchase_orders_approved_count=1,
            purchase_orders_cancelled_count=0,
            goods_receipts_count=1,
            supplier_invoices_posted_count=1,
            supplier_invoices_voided_count=0,
            supplier_payments_posted_count=1,
            supplier_payments_voided_count=0,
            supplier_payment_total=(Decimal("40000.00")),
            current_open_invoice_count=1,
            current_outstanding_liability=(Decimal("60000.00")),
            current_overdue_invoice_count=1,
        )
    )

    assert report.purchase_orders == (purchase_order,)
    assert report.goods_receipts == (goods_receipt,)
    assert report.supplier_invoices == (supplier_invoice,)
    assert report.supplier_payments == (supplier_payment,)

    assert report.open_supplier_invoices[0].pk == supplier_invoice.pk
    assert report.open_supplier_invoices[0].posted_payment_total == Decimal("40000.00")


@pytest.mark.django_db
def test_purchasing_report_separates_current_liability(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Retain current liability outside the activity period."""

    old_time = _event_time(days_ago=10)
    report_date = timezone.localdate() - timedelta(days=1)

    context = create_supplier_finance_context(
        context=purchasing_context,
        invoice_date=old_time.date(),
        due_date=(timezone.localdate() + timedelta(days=30)),
    )

    _align_activity_times(
        supplier_invoice_id=(context.supplier_invoice.pk),
        event_time=old_time,
    )

    report = get_purchasing_activity_report(
        date_range=ReportDateRange(
            start_date=report_date,
            end_date=report_date,
        ),
        as_of_date=timezone.localdate(),
    )

    assert report.summary == (
        PurchasingActivitySummary(
            currency="UGX",
            purchase_orders_created_count=0,
            purchase_orders_submitted_count=0,
            purchase_orders_approved_count=0,
            purchase_orders_cancelled_count=0,
            goods_receipts_count=0,
            supplier_invoices_posted_count=0,
            supplier_invoices_voided_count=0,
            supplier_payments_posted_count=0,
            supplier_payments_voided_count=0,
            supplier_payment_total=(Decimal("0.00")),
            current_open_invoice_count=1,
            current_outstanding_liability=(Decimal("100000.00")),
            current_overdue_invoice_count=0,
        )
    )

    assert report.purchase_orders == ()
    assert report.goods_receipts == ()
    assert report.supplier_invoices == ()
    assert report.supplier_payments == ()

    assert len(report.open_supplier_invoices) == 1


def test_purchasing_report_rejects_invalid_currency() -> None:
    """Require a valid reporting currency."""

    report_date = timezone.localdate()

    with pytest.raises(
        ValueError,
        match="three-letter code",
    ):
        get_purchasing_activity_report(
            date_range=ReportDateRange(
                start_date=report_date,
                end_date=report_date,
            ),
            currency="UGXA",
        )


@pytest.mark.django_db
def test_purchasing_report_uses_five_queries(
    purchasing_context: PurchasingTestContext,
    django_assert_num_queries,
) -> None:
    """Keep Purchasing reporting query-bounded."""

    event_time = _event_time()
    report_date = event_time.date()

    context = create_supplier_finance_context(
        context=purchasing_context,
        invoice_date=report_date,
        due_date=report_date,
        payment_amount=Decimal("40000.00"),
    )

    _align_activity_times(
        supplier_invoice_id=(context.supplier_invoice.pk),
        event_time=event_time,
    )

    with django_assert_num_queries(5):
        report = get_purchasing_activity_report(
            date_range=ReportDateRange(
                start_date=report_date,
                end_date=report_date,
            ),
            as_of_date=timezone.localdate(),
        )

        assert report.purchase_orders[0].supplier.name
        assert report.goods_receipts[0].purchase_order.purchase_order_number
        assert report.supplier_invoices[0].supplier.name
        assert report.supplier_payments[0].recorded_by.username
        assert report.open_supplier_invoices[0].posted_payment_total == Decimal(
            "40000.00"
        )
        assert report.open_supplier_invoices[0].outstanding_amount == Decimal(
            "60000.00"
        )

    assert report.summary.current_outstanding_liability == Decimal("60000.00")
