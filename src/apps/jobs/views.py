"""HTTP views for job-card intake and history workflows."""

from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.forms.forms import BaseForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import employee_permission_required
from apps.accounts.models import User
from apps.billing.calculations import InvoiceBalance
from apps.billing.models import Invoice
from apps.billing.selectors import get_invoice_balance
from apps.customers.models import Customer
from apps.jobs.constants import (
    FuelLevel,
    InspectionType,
    JobNoteType,
    JobPermissionName,
    JobPriority,
    JobStatus,
)
from apps.jobs.forms import (
    InspectionCreateForm,
    JobCardCancelForm,
    JobCardOpenForm,
    JobNoteCreateForm,
    VehicleReleaseForm,
)
from apps.jobs.models import (
    JobCard,
    VehicleRelease,
)
from apps.jobs.selectors import (
    get_job_card_by_id,
    get_job_inspections,
    get_job_notes,
    get_vehicle_release_by_id,
    get_vehicle_release_for_job,
    search_job_cards,
)
from apps.jobs.services.inspections import (
    AddInspectionCommand,
    AddJobNoteCommand,
    add_inspection,
    add_job_note,
)
from apps.jobs.services.intake import (
    CancelJobCardCommand,
    OpenJobCardCommand,
    cancel_job_card,
    open_job_card,
)
from apps.jobs.services.releases import (
    ReleaseVehicleCommand,
    release_vehicle,
)
from apps.quotations.selectors import (
    get_current_quotation_for_job,
    get_quotation_history_for_job,
)
from apps.vehicles.models import Vehicle
from apps.workshop.constants import WorkOrderStatus
from apps.workshop.models import WorkOrder


def _get_job_card_or_404(
    *,
    job_card_id: int,
) -> JobCard:
    """Return a job card or raise HTTP 404."""

    try:
        return get_job_card_by_id(job_card_id=job_card_id)
    except JobCard.DoesNotExist as exc:
        raise Http404("Job card not found.") from exc


def _get_vehicle_release_or_404(
    *,
    release_id: int,
) -> VehicleRelease:
    """Return a vehicle release or raise HTTP 404."""

    try:
        return get_vehicle_release_by_id(release_id=release_id)
    except VehicleRelease.DoesNotExist as exc:
        raise Http404("Vehicle-release record not found.") from exc


def _get_release_for_job(
    *,
    job_card_id: int,
) -> VehicleRelease | None:
    """Return the job's release record when present."""

    try:
        return get_vehicle_release_for_job(job_card_id=job_card_id)
    except VehicleRelease.DoesNotExist:
        return None


def _get_release_workflow(
    *,
    job_card_id: int,
) -> tuple[
    WorkOrder,
    Invoice,
    InvoiceBalance,
]:
    """Return workshop and billing release records."""

    try:
        work_order = WorkOrder.objects.select_related(
            "job_card",
        ).get(job_card_id=job_card_id)
    except WorkOrder.DoesNotExist as exc:
        raise Http404("This job has no workshop work order.") from exc

    try:
        invoice = Invoice.objects.get(work_order_id=work_order.pk)
    except Invoice.DoesNotExist as exc:
        raise Http404("This job has no customer invoice.") from exc

    balance = get_invoice_balance(invoice_id=invoice.pk)

    return (
        work_order,
        invoice,
        balance,
    )


def _minimum_release_mileage(
    *,
    job_card: JobCard,
) -> int:
    """Return the lowest allowed handover mileage."""

    minimum_mileage = job_card.arrival_mileage
    current_mileage = job_card.vehicle.current_mileage

    if current_mileage is not None:
        minimum_mileage = max(
            minimum_mileage,
            current_mileage,
        )

    return minimum_mileage


def _add_validation_error(
    *,
    form: BaseForm,
    error: ValidationError,
) -> None:
    """Add a domain validation error to a Django form."""

    if hasattr(error, "error_dict"):
        for field_name, field_errors in error.error_dict.items():
            target_field = field_name if field_name in form.fields else None

            for field_error in field_errors:
                form.add_error(target_field, field_error)

        return

    for message in error.messages:
        form.add_error(None, message)


def _validated_choice(
    *,
    value: str,
    allowed_values: set[str],
) -> str:
    """Return a recognized filter value or an empty value."""

    if value in allowed_values:
        return value

    return ""


@employee_permission_required(JobPermissionName.VIEW_JOB_CARD.value)
def job_list(request: HttpRequest) -> HttpResponse:
    """Display searchable and filterable job cards."""

    query = request.GET.get("q", "").strip()

    selected_status = _validated_choice(
        value=request.GET.get("status", ""),
        allowed_values={choice.value for choice in JobStatus},
    )
    selected_priority = _validated_choice(
        value=request.GET.get("priority", ""),
        allowed_values={choice.value for choice in JobPriority},
    )

    job_cards = search_job_cards(
        query=query,
        status=selected_status,
        priority=selected_priority,
    )

    paginator = Paginator(job_cards, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "jobs/job_list.html",
        {
            "page": page,
            "query": query,
            "selected_status": selected_status,
            "selected_priority": selected_priority,
            "status_choices": JobStatus.choices,
            "priority_choices": JobPriority.choices,
        },
    )


@employee_permission_required(JobPermissionName.ADD_JOB_CARD.value)
def job_create(request: HttpRequest) -> HttpResponse:
    """Open a job card for one customer and vehicle visit."""

    if request.method == "POST":
        form = JobCardOpenForm(request.POST)

        if form.is_valid():
            customer = cast(
                Customer,
                form.cleaned_data["customer"],
            )
            vehicle = cast(
                Vehicle,
                form.cleaned_data["vehicle"],
            )

            try:
                job_card = open_job_card(
                    actor=cast(User, request.user),
                    command=OpenJobCardCommand(
                        customer_id=cast(int, customer.pk),
                        vehicle_id=cast(int, vehicle.pk),
                        arrival_mileage=form.cleaned_data["arrival_mileage"],
                        customer_complaint=form.cleaned_data["customer_complaint"],
                        visible_condition=form.cleaned_data["visible_condition"],
                        fuel_level=FuelLevel(form.cleaned_data["fuel_level"]),
                        priority=JobPriority(form.cleaned_data["priority"]),
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (f"Job card {job_card.job_number} was opened successfully."),
                )

                return redirect(
                    "jobs:detail",
                    job_card_id=job_card.pk,
                )
    else:
        initial: dict[str, int] = {}

        customer_value = request.GET.get("customer", "")
        vehicle_value = request.GET.get("vehicle", "")

        if customer_value.isdecimal():
            initial["customer"] = int(customer_value)

        if vehicle_value.isdecimal():
            initial["vehicle"] = int(vehicle_value)

        form = JobCardOpenForm(initial=initial)

    return render(
        request,
        "jobs/job_form.html",
        {"form": form},
    )


@employee_permission_required(JobPermissionName.VIEW_JOB_CARD.value)
def job_detail(
    request: HttpRequest,
    job_card_id: int,
) -> HttpResponse:
    """Display a job card and its append-only history."""

    job_card = _get_job_card_or_404(job_card_id=job_card_id)
    vehicle_release = _get_release_for_job(job_card_id=job_card_id)

    release_available = False

    if vehicle_release is None and job_card.status in {
        JobStatus.OPEN,
        JobStatus.INSPECTED,
    }:
        try:
            work_order, invoice, _ = _get_release_workflow(job_card_id=job_card_id)
        except Http404:
            pass
        else:
            release_available = (
                work_order.status == WorkOrderStatus.COMPLETED
                and invoice.issued_at is not None
            )
    return render(
        request,
        "jobs/job_detail.html",
        {
            "job_card": job_card,
            "inspections": get_job_inspections(job_card_id=job_card_id),
            "notes": get_job_notes(job_card_id=job_card_id),
            "vehicle_release": vehicle_release,
            "release_available": release_available,
            "current_quotation": (
                get_current_quotation_for_job(job_card_id=job_card_id)
            ),
            "quotation_history": (
                get_quotation_history_for_job(job_card_id=job_card_id)
            ),
        },
    )


@employee_permission_required(JobPermissionName.ADD_INSPECTION.value)
def inspection_create(
    request: HttpRequest,
    job_card_id: int,
) -> HttpResponse:
    """Append an inspection to a job card."""

    job_card = _get_job_card_or_404(job_card_id=job_card_id)

    if request.method == "POST":
        form = InspectionCreateForm(request.POST)

        if form.is_valid():
            try:
                add_inspection(
                    actor=cast(User, request.user),
                    job_card_id=job_card_id,
                    command=AddInspectionCommand(
                        inspection_type=InspectionType(
                            form.cleaned_data["inspection_type"]
                        ),
                        findings=form.cleaned_data["findings"],
                        safety_observations=form.cleaned_data["safety_observations"],
                        recommended_action=form.cleaned_data["recommended_action"],
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    "The inspection was added successfully.",
                )

                return redirect(
                    "jobs:detail",
                    job_card_id=job_card_id,
                )
    else:
        form = InspectionCreateForm()

    return render(
        request,
        "jobs/inspection_form.html",
        {
            "job_card": job_card,
            "form": form,
        },
    )


@employee_permission_required(JobPermissionName.ADD_JOB_NOTE.value)
def note_create(
    request: HttpRequest,
    job_card_id: int,
) -> HttpResponse:
    """Append a note to a job card."""

    job_card = _get_job_card_or_404(job_card_id=job_card_id)

    if request.method == "POST":
        form = JobNoteCreateForm(request.POST)

        if form.is_valid():
            try:
                add_job_note(
                    actor=cast(User, request.user),
                    job_card_id=job_card_id,
                    command=AddJobNoteCommand(
                        note_type=JobNoteType(form.cleaned_data["note_type"]),
                        content=form.cleaned_data["content"],
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    "The job note was added successfully.",
                )

                return redirect(
                    "jobs:detail",
                    job_card_id=job_card_id,
                )
    else:
        form = JobNoteCreateForm()

    return render(
        request,
        "jobs/note_form.html",
        {
            "job_card": job_card,
            "form": form,
        },
    )


@employee_permission_required(JobPermissionName.CANCEL_JOB_CARD.value)
def job_cancel(
    request: HttpRequest,
    job_card_id: int,
) -> HttpResponse:
    """Cancel a job card while preserving its history."""

    job_card = _get_job_card_or_404(job_card_id=job_card_id)

    if request.method == "POST":
        form = JobCardCancelForm(request.POST)

        if form.is_valid():
            try:
                cancelled_job = cancel_job_card(
                    actor=cast(User, request.user),
                    job_card_id=job_card_id,
                    command=CancelJobCardCommand(reason=form.cleaned_data["reason"]),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (f"Job card {cancelled_job.job_number} was cancelled."),
                )

                return redirect(
                    "jobs:detail",
                    job_card_id=job_card_id,
                )
    else:
        form = JobCardCancelForm()

    return render(
        request,
        "jobs/cancel_form.html",
        {
            "job_card": job_card,
            "form": form,
        },
    )


@employee_permission_required(JobPermissionName.RELEASE_VEHICLE.value)
def vehicle_release_create(
    request: HttpRequest,
    job_card_id: int,
) -> HttpResponse:
    """Release a completed vehicle to its receiver."""

    job_card = _get_job_card_or_404(job_card_id=job_card_id)

    existing_release = _get_release_for_job(job_card_id=job_card_id)

    if existing_release is not None:
        return redirect(
            "jobs:release_detail",
            release_id=existing_release.pk,
        )

    work_order, invoice, balance = _get_release_workflow(job_card_id=job_card_id)

    actor = cast(User, request.user)
    allow_payment_override = actor.has_perm(
        JobPermissionName.OVERRIDE_VEHICLE_RELEASE_PAYMENT.value
    )
    minimum_mileage = _minimum_release_mileage(job_card=job_card)

    if request.method == "POST":
        form = VehicleReleaseForm(
            request.POST,
            minimum_mileage=minimum_mileage,
            allow_payment_override=(allow_payment_override),
        )

        if form.is_valid():
            try:
                vehicle_release = release_vehicle(
                    actor=actor,
                    command=ReleaseVehicleCommand(
                        job_card_id=job_card_id,
                        final_mileage=(form.cleaned_data["final_mileage"]),
                        final_condition=(form.cleaned_data["final_condition"]),
                        received_by_name=(form.cleaned_data["received_by_name"]),
                        received_by_contact=(form.cleaned_data["received_by_contact"]),
                        handover_notes=(form.cleaned_data["handover_notes"]),
                        payment_override=bool(
                            form.cleaned_data.get(
                                "payment_override",
                                False,
                            )
                        ),
                        payment_override_reason=str(
                            form.cleaned_data.get(
                                "payment_override_reason",
                                "",
                            )
                        ),
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (
                        f"Vehicle release "
                        f"{vehicle_release.release_number} "
                        "was recorded successfully."
                    ),
                )

                return redirect(
                    "jobs:release_detail",
                    release_id=vehicle_release.pk,
                )
    else:
        form = VehicleReleaseForm(
            minimum_mileage=minimum_mileage,
            allow_payment_override=(allow_payment_override),
        )

    return render(
        request,
        "jobs/release_form.html",
        {
            "job_card": job_card,
            "work_order": work_order,
            "invoice": invoice,
            "balance": balance,
            "has_outstanding_balance": (not balance.is_paid),
            "minimum_mileage": minimum_mileage,
            "allow_payment_override": (allow_payment_override),
            "form": form,
        },
    )


@employee_permission_required(JobPermissionName.VIEW_VEHICLE_RELEASE.value)
def vehicle_release_detail(
    request: HttpRequest,
    release_id: int,
) -> HttpResponse:
    """Display the permanent vehicle handover record."""

    vehicle_release = _get_vehicle_release_or_404(release_id=release_id)

    return render(
        request,
        "jobs/release_detail.html",
        {
            "vehicle_release": vehicle_release,
            "job_card": vehicle_release.job_card,
        },
    )
