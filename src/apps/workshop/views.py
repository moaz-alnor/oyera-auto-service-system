"""HTTP views for workshop execution workflows."""

from typing import cast

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from apps.accounts.decorators import (
    employee_permission_required,
)
from apps.accounts.models import User
from apps.workshop.constants import (
    WorkOrderStatus,
    WorkshopPermissionName,
    WorkTaskNoteType,
)
from apps.workshop.forms import (
    TechnicianAssignmentForm,
    TechnicianRemovalForm,
    WorkOrderCreateForm,
    WorkOrderHoldForm,
    WorkTaskBlockForm,
    WorkTaskNoteForm,
    WorkTaskReviewForm,
)
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkTask,
)
from apps.workshop.selectors import (
    get_work_order_by_id,
    search_work_orders,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    RemoveTechnicianCommand,
    assign_technician,
    remove_technician,
)
from apps.workshop.services.execution import (
    AddWorkTaskNoteCommand,
    BlockWorkTaskCommand,
    CompleteWorkOrderCommand,
    CompleteWorkTaskCommand,
    HoldWorkOrderCommand,
    ResumeWorkOrderCommand,
    StartWorkOrderCommand,
    StartWorkTaskCommand,
    SubmitWorkTaskForReviewCommand,
    add_work_task_note,
    block_work_task,
    complete_work_order,
    complete_work_task,
    hold_work_order,
    resume_work_order,
    start_work_order,
    start_work_task,
    submit_work_task_for_review,
)
from apps.workshop.services.work_orders import (
    CreateWorkOrderCommand,
    create_work_order,
)


def _add_validation_error(
    *,
    form: forms.Form,
    error: ValidationError,
) -> None:
    """Add a domain validation error to a browser form."""

    if hasattr(error, "message_dict"):
        for field_name, messages_list in error.message_dict.items():
            target_field = field_name if field_name in form.fields else None

            for message in messages_list:
                form.add_error(target_field, message)

        return

    for message in error.messages:
        form.add_error(None, message)


def _show_validation_error(
    *,
    request: HttpRequest,
    error: ValidationError,
) -> None:
    """Display domain validation messages after an action."""

    if hasattr(error, "message_dict"):
        for message_list in error.message_dict.values():
            for message in message_list:
                messages.error(request, message)

        return

    for message in error.messages:
        messages.error(request, message)


def _work_order_detail_redirect(
    *,
    work_order_id: int,
) -> HttpResponse:
    """Redirect to one workshop work order."""

    return redirect(
        "workshop:detail",
        work_order_id=work_order_id,
    )


@employee_permission_required(WorkshopPermissionName.VIEW_WORK_ORDER.value)
def work_order_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable workshop work orders."""

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    work_orders = search_work_orders(
        query=query,
        status=status,
    )

    return render(
        request,
        "workshop/work_order_list.html",
        {
            "work_orders": work_orders,
            "query": query,
            "selected_status": status,
            "status_choices": WorkOrderStatus.choices,
        },
    )


@employee_permission_required(WorkshopPermissionName.ADD_WORK_ORDER.value)
def work_order_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create workshop execution from an approved quotation."""

    if request.method == "POST":
        form = WorkOrderCreateForm(request.POST)

        if form.is_valid():
            quotation = form.cleaned_data["approved_quotation"]

            try:
                work_order = create_work_order(
                    actor=cast(User, request.user),
                    command=CreateWorkOrderCommand(
                        approved_quotation_id=quotation.pk,
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
                        f"Work order "
                        f"{work_order.work_order_number} "
                        "was created successfully."
                    ),
                )

                return redirect(
                    "workshop:detail",
                    work_order_id=work_order.pk,
                )
    else:
        form = WorkOrderCreateForm()

    return render(
        request,
        "workshop/work_order_form.html",
        {"form": form},
    )


@employee_permission_required(WorkshopPermissionName.VIEW_WORK_ORDER.value)
def work_order_detail(
    request: HttpRequest,
    work_order_id: int,
) -> HttpResponse:
    """Display one work order and its execution history."""

    try:
        work_order = get_work_order_by_id(work_order_id=work_order_id)
    except WorkOrder.DoesNotExist as exc:
        raise Http404("The requested work order does not exist.") from exc

    actor = cast(User, request.user)

    is_coordinator = actor.has_perm(WorkshopPermissionName.ASSIGN_TECHNICIAN.value)

    assigned_task_ids = set(
        TechnicianAssignment.objects.filter(
            work_task__work_order_id=work_order.pk,
            technician_id=actor.pk,
            is_active=True,
        ).values_list(
            "work_task_id",
            flat=True,
        )
    )

    task_rows = [
        {
            "task": task,
            "can_operate": (is_coordinator or task.pk in assigned_task_ids),
        }
        for task in work_order.tasks.all()
    ]

    return render(
        request,
        "workshop/work_order_detail.html",
        {
            "work_order": work_order,
            "task_rows": task_rows,
            "is_coordinator": is_coordinator,
        },
    )


@employee_permission_required(WorkshopPermissionName.ASSIGN_TECHNICIAN.value)
def technician_assignment_create(
    request: HttpRequest,
    work_task_id: int,
) -> HttpResponse:
    """Assign an eligible technician to a work task."""

    work_task = get_object_or_404(
        WorkTask.objects.select_related("work_order"),
        pk=work_task_id,
    )

    form = TechnicianAssignmentForm(request.POST or None)
    form.configure_for_task(work_task=work_task)

    if request.method == "POST" and form.is_valid():
        technician = cast(
            User,
            form.cleaned_data["technician"],
        )

        try:
            assignment = assign_technician(
                actor=cast(User, request.user),
                command=AssignTechnicianCommand(
                    work_task_id=work_task.pk,
                    technician_id=technician.pk,
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
                    f"{assignment.technician} was assigned to "
                    f"{work_task.service_name_snapshot}."
                ),
            )

            return _work_order_detail_redirect(work_order_id=work_task.work_order_id)

    return render(
        request,
        "workshop/technician_assignment_form.html",
        {
            "form": form,
            "work_task": work_task,
            "work_order": work_task.work_order,
        },
    )


@employee_permission_required(WorkshopPermissionName.ASSIGN_TECHNICIAN.value)
def technician_assignment_remove(
    request: HttpRequest,
    assignment_id: int,
) -> HttpResponse:
    """Remove a technician while preserving history."""

    assignment = get_object_or_404(
        TechnicianAssignment.objects.select_related(
            "technician",
            "work_task",
            "work_task__work_order",
        ),
        pk=assignment_id,
    )
    form = TechnicianRemovalForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            remove_technician(
                actor=cast(User, request.user),
                command=RemoveTechnicianCommand(
                    assignment_id=assignment.pk,
                    reason=form.cleaned_data["reason"],
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
                (f"{assignment.technician} was removed from the workshop task."),
            )

            return _work_order_detail_redirect(
                work_order_id=(assignment.work_task.work_order_id)
            )

    return render(
        request,
        "workshop/technician_removal_form.html",
        {
            "form": form,
            "assignment": assignment,
            "work_task": assignment.work_task,
            "work_order": assignment.work_task.work_order,
        },
    )


@employee_permission_required(WorkshopPermissionName.START_WORK_ORDER.value)
@require_POST
def work_order_start(
    request: HttpRequest,
    work_order_id: int,
) -> HttpResponse:
    """Start a ready workshop work order."""

    try:
        work_order = start_work_order(
            actor=cast(User, request.user),
            command=StartWorkOrderCommand(work_order_id=work_order_id),
        )
    except ValidationError as error:
        _show_validation_error(
            request=request,
            error=error,
        )
    else:
        messages.success(
            request,
            (f"Work order {work_order.work_order_number} is now in progress."),
        )

    return _work_order_detail_redirect(work_order_id=work_order_id)


@employee_permission_required(WorkshopPermissionName.HOLD_WORK_ORDER.value)
def work_order_hold(
    request: HttpRequest,
    work_order_id: int,
) -> HttpResponse:
    """Place an active work order on hold."""

    work_order = get_object_or_404(
        WorkOrder,
        pk=work_order_id,
    )
    form = WorkOrderHoldForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            hold_work_order(
                actor=cast(User, request.user),
                command=HoldWorkOrderCommand(
                    work_order_id=work_order.pk,
                    reason=form.cleaned_data["reason"],
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
                (f"Work order {work_order.work_order_number} was placed on hold."),
            )

            return _work_order_detail_redirect(work_order_id=work_order.pk)

    return render(
        request,
        "workshop/work_order_hold_form.html",
        {
            "form": form,
            "work_order": work_order,
        },
    )


@employee_permission_required(WorkshopPermissionName.RESUME_WORK_ORDER.value)
@require_POST
def work_order_resume(
    request: HttpRequest,
    work_order_id: int,
) -> HttpResponse:
    """Resume a held work order."""

    try:
        work_order = resume_work_order(
            actor=cast(User, request.user),
            command=ResumeWorkOrderCommand(work_order_id=work_order_id),
        )
    except ValidationError as error:
        _show_validation_error(
            request=request,
            error=error,
        )
    else:
        messages.success(
            request,
            (f"Work order {work_order.work_order_number} has resumed."),
        )

    return _work_order_detail_redirect(work_order_id=work_order_id)


@employee_permission_required(WorkshopPermissionName.COMPLETE_WORK_ORDER.value)
@require_POST
def work_order_complete(
    request: HttpRequest,
    work_order_id: int,
) -> HttpResponse:
    """Complete a work order after all tasks pass review."""

    try:
        work_order = complete_work_order(
            actor=cast(User, request.user),
            command=CompleteWorkOrderCommand(work_order_id=work_order_id),
        )
    except ValidationError as error:
        _show_validation_error(
            request=request,
            error=error,
        )
    else:
        messages.success(
            request,
            (f"Work order {work_order.work_order_number} was completed."),
        )

    return _work_order_detail_redirect(work_order_id=work_order_id)


@employee_permission_required(WorkshopPermissionName.START_WORK_TASK.value)
@require_POST
def work_task_start(
    request: HttpRequest,
    work_task_id: int,
) -> HttpResponse:
    """Start or resume an assigned workshop task."""

    work_task = get_object_or_404(
        WorkTask,
        pk=work_task_id,
    )

    try:
        started_task = start_work_task(
            actor=cast(User, request.user),
            command=StartWorkTaskCommand(work_task_id=work_task.pk),
        )
    except ValidationError as error:
        _show_validation_error(
            request=request,
            error=error,
        )
    else:
        messages.success(
            request,
            (f"{started_task.service_name_snapshot} is now in progress."),
        )

    return _work_order_detail_redirect(work_order_id=work_task.work_order_id)


@employee_permission_required(WorkshopPermissionName.BLOCK_WORK_TASK.value)
def work_task_block(
    request: HttpRequest,
    work_task_id: int,
) -> HttpResponse:
    """Record why an active task cannot continue."""

    work_task = get_object_or_404(
        WorkTask.objects.select_related("work_order"),
        pk=work_task_id,
    )
    form = WorkTaskBlockForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            block_work_task(
                actor=cast(User, request.user),
                command=BlockWorkTaskCommand(
                    work_task_id=work_task.pk,
                    reason=form.cleaned_data["reason"],
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
                (f"{work_task.service_name_snapshot} was marked as blocked."),
            )

            return _work_order_detail_redirect(work_order_id=work_task.work_order_id)

    return render(
        request,
        "workshop/task_block_form.html",
        {
            "form": form,
            "work_task": work_task,
            "work_order": work_task.work_order,
        },
    )


@employee_permission_required(WorkshopPermissionName.COMPLETE_WORK_TASK.value)
def work_task_submit_for_review(
    request: HttpRequest,
    work_task_id: int,
) -> HttpResponse:
    """Submit completed technical work for review."""

    work_task = get_object_or_404(
        WorkTask.objects.select_related("work_order"),
        pk=work_task_id,
    )
    form = WorkTaskReviewForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            submit_work_task_for_review(
                actor=cast(User, request.user),
                command=SubmitWorkTaskForReviewCommand(
                    work_task_id=work_task.pk,
                    completion_notes=(form.cleaned_data["completion_notes"]),
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
                (f"{work_task.service_name_snapshot} was submitted for review."),
            )

            return _work_order_detail_redirect(work_order_id=work_task.work_order_id)

    return render(
        request,
        "workshop/task_review_form.html",
        {
            "form": form,
            "work_task": work_task,
            "work_order": work_task.work_order,
        },
    )


@employee_permission_required(WorkshopPermissionName.COMPLETE_WORK_TASK.value)
@require_POST
def work_task_approve(
    request: HttpRequest,
    work_task_id: int,
) -> HttpResponse:
    """Approve a reviewed workshop task."""

    work_task = get_object_or_404(
        WorkTask,
        pk=work_task_id,
    )

    try:
        completed_task = complete_work_task(
            actor=cast(User, request.user),
            command=CompleteWorkTaskCommand(work_task_id=work_task.pk),
        )
    except ValidationError as error:
        _show_validation_error(
            request=request,
            error=error,
        )
    else:
        messages.success(
            request,
            (f"{completed_task.service_name_snapshot} was approved as complete."),
        )

    return _work_order_detail_redirect(work_order_id=work_task.work_order_id)


@employee_permission_required(WorkshopPermissionName.ADD_TASK_NOTE.value)
def work_task_note_create(
    request: HttpRequest,
    work_task_id: int,
) -> HttpResponse:
    """Append a note to a workshop task."""

    work_task = get_object_or_404(
        WorkTask.objects.select_related("work_order"),
        pk=work_task_id,
    )
    form = WorkTaskNoteForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        note_type = cast(
            WorkTaskNoteType,
            form.cleaned_data["note_type"],
        )

        try:
            add_work_task_note(
                actor=cast(User, request.user),
                command=AddWorkTaskNoteCommand(
                    work_task_id=work_task.pk,
                    note_type=note_type,
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
                "The workshop note was added.",
            )

            return _work_order_detail_redirect(work_order_id=work_task.work_order_id)

    return render(
        request,
        "workshop/task_note_form.html",
        {
            "form": form,
            "work_task": work_task,
            "work_order": work_task.work_order,
        },
    )
