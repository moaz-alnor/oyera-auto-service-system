"""Application services for supplier-payment workflows."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.purchasing.calculations import round_money
from apps.purchasing.constants import (
    PurchasingPermissionName,
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    SupplierInvoice,
    SupplierPayment,
)


@dataclass(frozen=True, slots=True)
class RecordSupplierPaymentCommand:
    """Contain one supplier-payment request."""

    amount: Decimal
    method: SupplierPaymentMethod
    external_reference: str = ""
    paid_at: datetime | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class VoidSupplierPaymentCommand:
    """Contain a supplier-payment void reason."""

    reason: str


def _require_permission(
    *,
    actor: User,
    permission: PurchasingPermissionName,
) -> None:
    """Require one supplier-payment permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this supplier-payment action."
        )


def _supplier_payment_number(
    *,
    supplier_invoice_id: int,
    sequence: int,
) -> str:
    """Return a readable supplier-payment number."""

    return f"SPAY-{supplier_invoice_id:06d}-{sequence:02d}"


def _posted_payment_total(
    *,
    supplier_invoice_id: int,
) -> Decimal:
    """Return active payments against one invoice."""

    return SupplierPayment.objects.filter(
        supplier_invoice_id=supplier_invoice_id,
        status=SupplierPaymentStatus.POSTED,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


def _supplier_invoice_status_for_payment_total(
    *,
    invoice_total: Decimal,
    paid_amount: Decimal,
) -> SupplierInvoiceStatus:
    """Return invoice status for its active payments."""

    normalised_total = round_money(invoice_total)
    normalised_paid_amount = round_money(paid_amount)

    if normalised_paid_amount < Decimal("0.00"):
        raise ValidationError(
            {"payments": ("Posted supplier-payment total cannot be negative.")}
        )

    if normalised_paid_amount > normalised_total:
        raise ValidationError(
            {"payments": ("Posted supplier payments cannot exceed the invoice total.")}
        )

    if normalised_paid_amount == Decimal("0.00"):
        return SupplierInvoiceStatus.POSTED

    if normalised_paid_amount < normalised_total:
        return SupplierInvoiceStatus.PARTIALLY_PAID

    return SupplierInvoiceStatus.PAID


def _get_locked_supplier_invoice(
    *,
    supplier_invoice_id: int,
) -> SupplierInvoice:
    """Return one locked supplier invoice."""

    try:
        return SupplierInvoice.objects.select_for_update().get(pk=supplier_invoice_id)
    except SupplierInvoice.DoesNotExist as exc:
        raise ValidationError(
            {"supplier_invoice": ("The selected supplier invoice does not exist.")}
        ) from exc


@transaction.atomic
def record_supplier_payment(
    *,
    actor: User,
    supplier_invoice_id: int,
    command: RecordSupplierPaymentCommand,
) -> SupplierPayment:
    """Record one active supplier payment."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.RECORD_SUPPLIER_PAYMENT),
    )

    amount = round_money(command.amount)

    if amount <= Decimal("0.00"):
        raise ValidationError(
            {"amount": ("Supplier payment must be greater than zero.")}
        )

    supplier_invoice = _get_locked_supplier_invoice(
        supplier_invoice_id=supplier_invoice_id
    )

    allowed_statuses = {
        SupplierInvoiceStatus.POSTED,
        SupplierInvoiceStatus.PARTIALLY_PAID,
    }

    if supplier_invoice.status not in allowed_statuses:
        raise ValidationError(
            {
                "supplier_invoice": (
                    "Payments can only be recorded "
                    "against a posted supplier invoice "
                    "with an outstanding balance."
                )
            }
        )

    paid_amount = _posted_payment_total(supplier_invoice_id=supplier_invoice.pk)
    outstanding_amount = round_money(supplier_invoice.total - paid_amount)

    if amount > outstanding_amount:
        raise ValidationError(
            {
                "amount": (
                    "Supplier payment cannot exceed the outstanding invoice balance."
                )
            }
        )

    sequence = (
        SupplierPayment.objects.filter(supplier_invoice=supplier_invoice).count() + 1
    )

    payment = SupplierPayment(
        payment_number=_supplier_payment_number(
            supplier_invoice_id=supplier_invoice.pk,
            sequence=sequence,
        ),
        supplier_invoice=supplier_invoice,
        amount=amount,
        currency=supplier_invoice.currency,
        method=command.method,
        status=SupplierPaymentStatus.POSTED,
        external_reference=(command.external_reference),
        paid_at=command.paid_at or timezone.now(),
        notes=command.notes,
        recorded_by=actor,
    )
    payment.full_clean()
    payment.save()

    new_paid_amount = round_money(paid_amount + amount)

    supplier_invoice.status = _supplier_invoice_status_for_payment_total(
        invoice_total=supplier_invoice.total,
        paid_amount=new_paid_amount,
    )
    supplier_invoice.updated_by = actor

    supplier_invoice.full_clean()
    supplier_invoice.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    return payment


@transaction.atomic
def void_supplier_payment(
    *,
    actor: User,
    payment_id: int,
    command: VoidSupplierPaymentCommand,
) -> SupplierPayment:
    """Void a payment and recalculate invoice status."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.VOID_SUPPLIER_PAYMENT),
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError(
            {"reason": ("Record why the supplier payment is being voided.")}
        )

    try:
        payment = SupplierPayment.objects.select_for_update().get(pk=payment_id)
    except SupplierPayment.DoesNotExist as exc:
        raise ValidationError(
            {"payment": ("The selected supplier payment does not exist.")}
        ) from exc

    supplier_invoice = _get_locked_supplier_invoice(
        supplier_invoice_id=(payment.supplier_invoice_id)
    )

    if payment.status != SupplierPaymentStatus.POSTED:
        raise ValidationError(
            {"payment": ("Only a posted supplier payment can be voided.")}
        )

    if supplier_invoice.status == SupplierInvoiceStatus.VOIDED:
        raise ValidationError(
            {
                "supplier_invoice": (
                    "A supplier payment cannot be changed after its invoice is voided."
                )
            }
        )

    payment.supplier_invoice = supplier_invoice
    payment.status = SupplierPaymentStatus.VOIDED
    payment.voided_at = timezone.now()
    payment.voided_by = actor
    payment.void_reason = reason

    payment.full_clean()
    payment.save(
        update_fields=(
            "status",
            "voided_at",
            "voided_by",
            "void_reason",
            "updated_at",
        )
    )

    paid_amount = _posted_payment_total(supplier_invoice_id=supplier_invoice.pk)

    supplier_invoice.status = _supplier_invoice_status_for_payment_total(
        invoice_total=supplier_invoice.total,
        paid_amount=paid_amount,
    )
    supplier_invoice.updated_by = actor

    supplier_invoice.full_clean()
    supplier_invoice.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    return payment
