"""Application services for invoice-payment workflows."""

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
from apps.billing.calculations import quantize_money
from apps.billing.constants import (
    BillingPermissionName,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    Payment,
)


@dataclass(frozen=True, slots=True)
class RecordPaymentCommand:
    """Contain one customer payment request."""

    amount: Decimal
    payment_method: PaymentMethod
    external_reference: str = ""
    paid_at: datetime | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class VoidPaymentCommand:
    """Contain a payment-voiding reason."""

    reason: str


def _require_permission(
    *,
    actor: User,
    permission: BillingPermissionName,
) -> None:
    """Require one billing permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this billing action."
        )


def _payment_number(
    *,
    invoice_id: int,
    sequence: int,
) -> str:
    """Return a readable invoice-payment number."""

    return f"PAY-{invoice_id:06d}-{sequence:02d}"


def _posted_payment_total(
    *,
    invoice_id: int,
) -> Decimal:
    """Return the total of active posted payments."""

    return Payment.objects.filter(
        invoice_id=invoice_id,
        status=PaymentStatus.POSTED,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


def _invoice_status_for_payment_total(
    *,
    invoice_total: Decimal,
    paid_amount: Decimal,
) -> InvoiceStatus:
    """Return invoice status for its posted balance."""

    normalized_total = quantize_money(invoice_total)
    normalized_paid_amount = quantize_money(paid_amount)

    if normalized_paid_amount < Decimal("0.00"):
        raise ValidationError(
            {"payments": ("Posted payment total cannot be negative.")}
        )

    if normalized_paid_amount > normalized_total:
        raise ValidationError(
            {"payments": ("Posted payments cannot exceed the invoice total.")}
        )

    if normalized_paid_amount == Decimal("0.00"):
        return InvoiceStatus.ISSUED

    if normalized_paid_amount < normalized_total:
        return InvoiceStatus.PARTIALLY_PAID

    return InvoiceStatus.PAID


@transaction.atomic
def record_payment(
    *,
    actor: User,
    invoice_id: int,
    command: RecordPaymentCommand,
) -> Payment:
    """Record one posted customer payment."""

    _require_permission(
        actor=actor,
        permission=(BillingPermissionName.RECORD_PAYMENT),
    )

    amount = quantize_money(command.amount)

    if amount <= Decimal("0.00"):
        raise ValidationError({"amount": ("Payment amount must be greater than zero.")})

    try:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise ValidationError(
            {"invoice": ("The selected invoice does not exist.")}
        ) from exc

    allowed_statuses = {
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
    }

    if invoice.status not in allowed_statuses:
        raise ValidationError(
            {
                "invoice": (
                    "Payments can only be recorded against "
                    "an issued invoice with an outstanding "
                    "balance."
                )
            }
        )

    paid_amount = _posted_payment_total(invoice_id=invoice.pk)
    outstanding_amount = quantize_money(invoice.total - paid_amount)

    if amount > outstanding_amount:
        raise ValidationError(
            {"amount": ("Payment cannot exceed the outstanding invoice balance.")}
        )

    sequence = Payment.objects.filter(invoice=invoice).count() + 1

    payment = Payment(
        payment_number=_payment_number(
            invoice_id=invoice.pk,
            sequence=sequence,
        ),
        invoice=invoice,
        status=PaymentStatus.POSTED,
        amount=amount,
        currency=invoice.currency,
        payment_method=command.payment_method,
        external_reference=(command.external_reference),
        paid_at=command.paid_at or timezone.now(),
        notes=command.notes,
        received_by=actor,
    )
    payment.full_clean()
    payment.save()

    new_paid_amount = quantize_money(paid_amount + amount)

    invoice.status = _invoice_status_for_payment_total(
        invoice_total=invoice.total,
        paid_amount=new_paid_amount,
    )
    invoice.updated_by = actor

    invoice.full_clean()
    invoice.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    return payment


@transaction.atomic
def void_payment(
    *,
    actor: User,
    payment_id: int,
    command: VoidPaymentCommand,
) -> Payment:
    """Void a posted payment and recalculate invoice state."""

    _require_permission(
        actor=actor,
        permission=BillingPermissionName.VOID_PAYMENT,
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError({"reason": ("Record why the payment is being voided.")})

    try:
        payment = Payment.objects.select_for_update().get(pk=payment_id)
    except Payment.DoesNotExist as exc:
        raise ValidationError(
            {"payment": ("The selected payment does not exist.")}
        ) from exc

    invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)

    if payment.status != PaymentStatus.POSTED:
        raise ValidationError({"payment": ("Only a posted payment can be voided.")})

    if invoice.status == InvoiceStatus.VOIDED:
        raise ValidationError(
            {"invoice": ("A payment cannot be changed after its invoice is voided.")}
        )

    payment.invoice = invoice
    payment.status = PaymentStatus.VOIDED
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

    paid_amount = _posted_payment_total(invoice_id=invoice.pk)

    invoice.status = _invoice_status_for_payment_total(
        invoice_total=invoice.total,
        paid_amount=paid_amount,
    )
    invoice.updated_by = actor

    invoice.full_clean()
    invoice.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    return payment
