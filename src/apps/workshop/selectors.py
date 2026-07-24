"""Read-only queries for workshop planning and execution."""

from django.db.models import Prefetch, Q, QuerySet

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.quotations.constants import QuotationStatus
from apps.quotations.models import Quotation
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkProductRequirement,
    WorkTask,
    WorkTaskNote,
)


def search_work_orders(
    *,
    query: str = "",
    status: str = "",
) -> QuerySet[WorkOrder]:
    """Return work orders matching workshop filters."""

    work_orders = WorkOrder.objects.select_related(
        "job_card",
        "approved_quotation",
        "created_by",
        "updated_by",
    )

    if status:
        work_orders = work_orders.filter(status=status)

    search_value = query.strip()

    if not search_value:
        return work_orders

    return work_orders.filter(
        Q(work_order_number__icontains=search_value)
        | Q(job_card__job_number__icontains=search_value)
        | Q(job_card__customer_name_snapshot__icontains=(search_value))
        | Q(job_card__customer_phone_snapshot__icontains=(search_value))
        | Q(job_card__vehicle_registration_snapshot__icontains=(search_value))
        | Q(approved_quotation__quotation_number__icontains=(search_value))
    )


def get_work_order_by_id(
    *,
    work_order_id: int,
) -> WorkOrder:
    """Return one work order with its execution records."""

    assignments = TechnicianAssignment.objects.select_related(
        "technician",
        "assigned_by",
    ).order_by(
        "-is_active",
        "-assigned_at",
        "-pk",
    )

    notes = WorkTaskNote.objects.select_related(
        "created_by",
    ).order_by(
        "-created_at",
        "-pk",
    )

    tasks = (
        WorkTask.objects.select_related(
            "source_service_line",
            "created_by",
            "updated_by",
        )
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=assignments,
            ),
            Prefetch(
                "notes",
                queryset=notes,
            ),
        )
        .order_by(
            "position",
            "pk",
        )
    )

    product_requirements = WorkProductRequirement.objects.select_related(
        "source_product_line",
        "created_by",
    ).order_by(
        "position",
        "pk",
    )

    return (
        WorkOrder.objects.select_related(
            "job_card",
            "job_card__customer",
            "job_card__vehicle",
            "approved_quotation",
            "created_by",
            "updated_by",
        )
        .prefetch_related(
            Prefetch(
                "tasks",
                queryset=tasks,
            ),
            Prefetch(
                "product_requirements",
                queryset=product_requirements,
            ),
        )
        .get(pk=work_order_id)
    )


def get_work_orders_for_technician(
    *,
    technician_id: int,
) -> QuerySet[WorkOrder]:
    """Return work orders actively assigned to a technician."""

    return (
        WorkOrder.objects.filter(
            tasks__assignments__technician_id=technician_id,
            tasks__assignments__is_active=True,
        )
        .select_related(
            "job_card",
            "approved_quotation",
        )
        .distinct()
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def get_available_technicians() -> QuerySet[User]:
    """Return active technicians eligible for assignment."""

    technician_roles = (
        RoleName.TECHNICIAN.value,
        RoleName.SENIOR_TECHNICIAN.value,
    )

    return (
        User.objects.filter(
            is_active=True,
            groups__name__in=technician_roles,
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )


def get_approved_quotations_available_for_work_order() -> QuerySet[Quotation]:
    """Return approved quotations not yet used for execution."""

    return (
        Quotation.objects.filter(
            status=QuotationStatus.APPROVED,
            is_current=True,
            work_order__isnull=True,
        )
        .select_related(
            "job_card",
            "job_card__customer",
            "job_card__vehicle",
        )
        .order_by(
            "-decision_at",
            "-created_at",
        )
    )


def get_available_technicians_for_task(
    *,
    work_task_id: int,
) -> QuerySet[User]:
    """Return eligible technicians not assigned to a task."""

    active_technician_ids = TechnicianAssignment.objects.filter(
        work_task_id=work_task_id,
        is_active=True,
    ).values_list(
        "technician_id",
        flat=True,
    )

    return get_available_technicians().exclude(pk__in=active_technician_ids)
