"""Tests for vehicle-release application services."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.utils import timezone

from apps.billing.constants import PaymentMethod
from apps.billing.models import Invoice
from apps.billing.services.invoices import (
    CreateInvoiceCommand,
    IssueInvoiceCommand,
    create_invoice,
    issue_invoice,
)
from apps.billing.services.payments import (
    RecordPaymentCommand,
    record_payment,
)
from apps.jobs.constants import JobStatus
from apps.jobs.models import VehicleRelease
from apps.jobs.services.releases import (
    ReleaseVehicleCommand,
    release_vehicle,
)
from apps.jobs.tests.conftest import ReleaseTestContext
from apps.workshop.constants import (
    WorkOrderStatus,
    WorkTaskStatus,
)


def _complete_work_order(
    *,
    context: ReleaseTestContext,
) -> None:
    """Mark the fixture work order as completed."""

    now = timezone.now()
    task = context.work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for vehicle-release tests."
    task.updated_by = context.manager
    task.full_clean()
    task.save()

    context.work_order.status = WorkOrderStatus.COMPLETED
    context.work_order.started_at = now
    context.work_order.completed_at = now
    context.work_order.updated_by = context.manager
    context.work_order.full_clean()
    context.work_order.save()

    context.work_order.refresh_from_db()


def _create_draft_invoice(
    *,
    context: ReleaseTestContext,
) -> Invoice:
    """Complete work and create a draft invoice."""

    _complete_work_order(context=context)

    return create_invoice(
        actor=context.manager,
        work_order_id=context.work_order.pk,
        command=CreateInvoiceCommand(),
    )


def _issue_invoice(
    *,
    context: ReleaseTestContext,
) -> Invoice:
    """Create and issue the fixture invoice."""

    invoice = _create_draft_invoice(context=context)

    return issue_invoice(
        actor=context.cashier,
        invoice_id=invoice.pk,
        command=IssueInvoiceCommand(
            due_date=(timezone.localdate() + timedelta(days=14))
        ),
    )


def _pay_invoice(
    *,
    context: ReleaseTestContext,
) -> Invoice:
    """Create and fully pay the fixture invoice."""

    invoice = _issue_invoice(context=context)

    record_payment(
        actor=context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=invoice.total,
            payment_method=PaymentMethod.CASH,
        ),
    )

    invoice.refresh_from_db()

    return invoice


def _release_command(
    *,
    context: ReleaseTestContext,
    final_mileage: int = 45100,
    payment_override: bool = False,
    payment_override_reason: str = "",
) -> ReleaseVehicleCommand:
    """Return a standard handover command."""

    return ReleaseVehicleCommand(
        job_card_id=context.job_card.pk,
        final_mileage=final_mileage,
        final_condition=("Vehicle clean and operating normally."),
        received_by_name="Amina Musa",
        received_by_contact="0700222333",
        handover_notes=("Vehicle keys and documents handed over."),
        payment_override=payment_override,
        payment_override_reason=(payment_override_reason),
    )


@pytest.mark.django_db
def test_receptionist_releases_fully_paid_vehicle(
    release_context: ReleaseTestContext,
) -> None:
    """Allow normal paid handover by reception staff."""

    invoice = _pay_invoice(context=release_context)

    release = release_vehicle(
        actor=release_context.receptionist,
        command=_release_command(context=release_context),
    )

    release_context.job_card.refresh_from_db()
    release_context.job_card.vehicle.refresh_from_db()

    assert release.release_number == (f"REL-{release_context.job_card.pk:06d}")
    assert release.invoice_number_snapshot == (invoice.invoice_number)
    assert release.paid_amount_snapshot == Decimal("80000.00")
    assert release.outstanding_amount_snapshot == Decimal("0.00")
    assert release.payment_override is False
    assert release_context.job_card.status == (JobStatus.RELEASED)
    assert release_context.job_card.vehicle.current_mileage == 45100


@pytest.mark.django_db
def test_release_handles_vehicle_without_current_mileage(
    release_context: ReleaseTestContext,
) -> None:
    """Use arrival mileage when current mileage is unknown."""

    _pay_invoice(context=release_context)

    vehicle = release_context.job_card.vehicle
    vehicle.current_mileage = None
    vehicle.save(update_fields=("current_mileage",))

    release = release_vehicle(
        actor=release_context.receptionist,
        command=_release_command(
            context=release_context,
            final_mileage=45050,
        ),
    )

    vehicle.refresh_from_db()

    assert release.final_mileage == 45050
    assert vehicle.current_mileage == 45050


@pytest.mark.django_db
def test_technician_cannot_release_vehicle(
    release_context: ReleaseTestContext,
) -> None:
    """Reject employees without release authority."""

    with pytest.raises(PermissionDenied):
        release_vehicle(
            actor=release_context.technician,
            command=_release_command(context=release_context),
        )


@pytest.mark.django_db
def test_unfinished_work_order_cannot_be_released(
    release_context: ReleaseTestContext,
) -> None:
    """Require completed workshop work."""

    with pytest.raises(ValidationError) as exc_info:
        release_vehicle(
            actor=release_context.manager,
            command=_release_command(context=release_context),
        )

    assert "work_order" in exc_info.value.message_dict


@pytest.mark.django_db
def test_draft_invoice_cannot_support_release(
    release_context: ReleaseTestContext,
) -> None:
    """Require the customer invoice to be issued."""

    _create_draft_invoice(context=release_context)

    with pytest.raises(ValidationError) as exc_info:
        release_vehicle(
            actor=release_context.manager,
            command=_release_command(context=release_context),
        )

    assert "invoice" in exc_info.value.message_dict


@pytest.mark.django_db
def test_unpaid_invoice_requires_override(
    release_context: ReleaseTestContext,
) -> None:
    """Block unpaid release without authorisation."""

    _issue_invoice(context=release_context)

    with pytest.raises(ValidationError) as exc_info:
        release_vehicle(
            actor=release_context.manager,
            command=_release_command(context=release_context),
        )

    assert "payment_override" in (exc_info.value.message_dict)


@pytest.mark.django_db
def test_receptionist_cannot_override_payment(
    release_context: ReleaseTestContext,
) -> None:
    """Reserve unpaid release for management."""

    _issue_invoice(context=release_context)

    with pytest.raises(PermissionDenied):
        release_vehicle(
            actor=release_context.receptionist,
            command=_release_command(
                context=release_context,
                payment_override=True,
                payment_override_reason=("Customer approved corporate credit."),
            ),
        )


@pytest.mark.django_db
def test_manager_releases_with_partial_payment_override(
    release_context: ReleaseTestContext,
) -> None:
    """Preserve partial-payment override evidence."""

    invoice = _issue_invoice(context=release_context)

    record_payment(
        actor=release_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    release = release_vehicle(
        actor=release_context.manager,
        command=_release_command(
            context=release_context,
            payment_override=True,
            payment_override_reason=("  Manager approved corporate credit.  "),
        ),
    )

    assert release.paid_amount_snapshot == Decimal("30000.00")
    assert release.outstanding_amount_snapshot == Decimal("50000.00")
    assert release.payment_override is True
    assert release.payment_override_by == (release_context.manager)
    assert release.payment_override_at is not None
    assert release.payment_override_reason == ("Manager approved corporate credit.")


@pytest.mark.django_db
def test_failed_release_rolls_back_job_and_mileage(
    release_context: ReleaseTestContext,
) -> None:
    """Keep the workflow unchanged after validation failure."""

    _pay_invoice(context=release_context)

    with pytest.raises(ValidationError):
        release_vehicle(
            actor=release_context.receptionist,
            command=_release_command(
                context=release_context,
                final_mileage=44999,
            ),
        )

    release_context.job_card.refresh_from_db()
    release_context.job_card.vehicle.refresh_from_db()

    assert release_context.job_card.status == JobStatus.OPEN
    assert release_context.job_card.vehicle.current_mileage == 45000
    assert VehicleRelease.objects.count() == 0


@pytest.mark.django_db
def test_vehicle_cannot_be_released_twice(
    release_context: ReleaseTestContext,
) -> None:
    """Reject duplicate handover records."""

    _pay_invoice(context=release_context)

    release_vehicle(
        actor=release_context.receptionist,
        command=_release_command(context=release_context),
    )

    with pytest.raises(ValidationError) as exc_info:
        release_vehicle(
            actor=release_context.manager,
            command=_release_command(context=release_context),
        )

    assert "job_card" in exc_info.value.message_dict
    assert VehicleRelease.objects.count() == 1
