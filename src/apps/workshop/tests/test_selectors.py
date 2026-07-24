"""Tests for workshop read queries."""

import pytest

from apps.workshop.constants import WorkOrderStatus
from apps.workshop.selectors import (
    get_available_technicians,
    get_work_order_by_id,
    get_work_orders_for_technician,
    search_work_orders,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    assign_technician,
)
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)


@pytest.mark.django_db
def test_work_order_search_matches_customer_and_vehicle(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Search work orders using preserved job snapshots."""

    work_order = workshop_execution_context.work_order

    customer_results = search_work_orders(query="Daniel Kato")
    vehicle_results = search_work_orders(query="UBD 945X")

    assert list(customer_results) == [work_order]
    assert list(vehicle_results) == [work_order]


@pytest.mark.django_db
def test_work_order_search_filters_status(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Filter workshop records by operational status."""

    work_order = workshop_execution_context.work_order

    planned_results = search_work_orders(status=WorkOrderStatus.PLANNED)
    completed_results = search_work_orders(status=WorkOrderStatus.COMPLETED)

    assert list(planned_results) == [work_order]
    assert not completed_results.exists()


@pytest.mark.django_db
def test_detail_selector_returns_assignments(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Load task assignments for work-order display."""

    task = workshop_execution_context.work_order.tasks.get()

    assignment = assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    selected = get_work_order_by_id(
        work_order_id=(workshop_execution_context.work_order.pk)
    )
    selected_task = selected.tasks.get()
    selected_assignment = selected_task.assignments.get(pk=assignment.pk)

    assert selected_task.service_name_snapshot == ("Workshop Brake Service")
    assert selected_assignment.technician == workshop_execution_context.technician


@pytest.mark.django_db
def test_technician_queries_follow_assignment_rules(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Return eligible technicians and assigned work orders."""

    task = workshop_execution_context.work_order.tasks.get()

    assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    technicians = get_available_technicians()
    assigned_orders = get_work_orders_for_technician(
        technician_id=(workshop_execution_context.technician.pk)
    )

    assert workshop_execution_context.technician in technicians
    assert workshop_execution_context.second_technician in technicians
    assert workshop_execution_context.receptionist not in technicians
    assert workshop_execution_context.manager not in technicians
    assert workshop_execution_context.work_order in assigned_orders
