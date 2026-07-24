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
)
from apps.jobs.models import JobCard
from apps.jobs.selectors import (
    get_job_card_by_id,
    get_job_inspections,
    get_job_notes,
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
from apps.quotations.selectors import (
    get_current_quotation_for_job,
    get_quotation_history_for_job,
)
from apps.vehicles.models import Vehicle


def _get_job_card_or_404(
    *,
    job_card_id: int,
) -> JobCard:
    """Return a job card or raise HTTP 404."""

    try:
        return get_job_card_by_id(job_card_id=job_card_id)
    except JobCard.DoesNotExist as exc:
        raise Http404("Job card not found.") from exc


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

    return render(
        request,
        "jobs/job_detail.html",
        {
            "job_card": job_card,
            "inspections": get_job_inspections(job_card_id=job_card_id),
            "notes": get_job_notes(job_card_id=job_card_id),
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
