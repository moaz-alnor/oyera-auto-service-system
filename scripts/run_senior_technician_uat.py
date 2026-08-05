"""Execute Senior Technician browser UAT and capture evidence."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final

import django
from django.apps import apps
from django.core.management import call_command
from playwright.sync_api import Page, sync_playwright
from run_administrator_uat import (
    CaseResult,
    full_url,
    login,
    require,
    require_response,
    stop_server,
    submit_form,
    wait_for_server,
)
from run_receptionist_uat import select_option_containing

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

django.setup()

ROOT_DIR: Final = Path(__file__).resolve().parents[1]

EVIDENCE_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "senior-technician"
LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"
SERVER_LOG: Final = Path("/tmp/oyera-senior-technician-uat-server.log")

RESERVATION_NOTE: Final = "Issued during Senior Technician UAT."
RETURN_NOTE: Final = "Unused filter quantity returned during UAT."
HOLD_REASON: Final = "UAT pause while confirming workshop equipment."
TASK_NOTE: Final = "Senior Technician verified the assigned UAT task."

RESULTS: dict[str, CaseResult] = {
    "UAT-SEN-01": CaseResult(),
    "UAT-SEN-02": CaseResult(),
    "UAT-SEN-03": CaseResult(),
    "UAT-SEN-04": CaseResult(),
    "UAT-SEN-05": CaseResult(),
    "UAT-SEN-06": CaseResult(),
}


@dataclass(frozen=True)
class Scenario:
    """Store IDs and starting values outside Playwright."""

    reserve_requirement_id: int
    inventory_item_id: int
    issue_reservation_id: int
    return_issue_id: int
    work_order_id: int
    task_id: int
    initial_issue_quantity: Decimal
    initial_return_count: int


def start_server() -> subprocess.Popen[str]:
    """Start the dedicated Senior Technician UAT server."""
    log_file = SERVER_LOG.open(
        "w",
        encoding="utf-8",
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "src/manage.py",
            "runserver",
            "127.0.0.1:8000",
            "--noreload",
        ],
        cwd=ROOT_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )

    log_file.close()

    try:
        wait_for_server()
    except Exception:
        process.terminate()
        process.wait(timeout=10)
        raise

    return process


def capture(
    page: Page,
    filename: str,
) -> Path:
    """Capture one full-page screenshot."""
    destination = EVIDENCE_DIR / filename

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    page.screenshot(
        path=destination,
        full_page=True,
    )

    return destination


def clear_evidence() -> None:
    """Remove evidence left by an incomplete run."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in EVIDENCE_DIR.glob("UAT-SEN-*"):
        path.unlink(missing_ok=True)


def reset_ledger_rows() -> None:
    """Return Senior Technician ledger rows to NOT RUN."""
    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()

    updated: list[str] = []

    for line in lines:
        case_id = next(
            (case for case in RESULTS if line.startswith(f"| {case} |")),
            None,
        )

        if case_id is None:
            updated.append(line)
        else:
            updated.append(f"| {case_id} | NOT RUN |  |  |  |")

    LEDGER_PATH.write_text(
        "\n".join(updated) + "\n",
        encoding="utf-8",
    )


def write_results() -> None:
    """Write actual Senior Technician results."""
    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()

    updated: list[str] = []

    for line in lines:
        case_id = next(
            (case for case in RESULTS if line.startswith(f"| {case} |")),
            None,
        )

        if case_id is None:
            updated.append(line)
            continue

        result = RESULTS[case_id]

        updated.append(
            f"| {case_id} "
            f"| {result.status} "
            f"| {result.evidence} "
            f"| {result.issue} "
            f"| {result.notes} |"
        )

    LEDGER_PATH.write_text(
        "\n".join(updated) + "\n",
        encoding="utf-8",
    )


def prepare_scenario() -> Scenario:
    """Resolve all seeded scenarios before Playwright starts."""
    requirement_model = apps.get_model(
        "workshop",
        "WorkProductRequirement",
    )
    inventory_item_model = apps.get_model(
        "inventory",
        "InventoryItem",
    )
    reservation_model = apps.get_model(
        "inventory",
        "StockReservation",
    )
    movement_model = apps.get_model(
        "inventory",
        "StockMovement",
    )
    work_order_model = apps.get_model(
        "workshop",
        "WorkOrder",
    )

    reserve_requirement = requirement_model.objects.get(
        work_order__job_card__vehicle__registration_number=("UAT 101A"),
    )

    inventory_item = inventory_item_model.objects.get(
        product__sku="OIL-FILTER-001",
    )

    issue_reservation = reservation_model.objects.get(
        **{
            (
                "work_product_requirement__work_order__"
                "job_card__vehicle__registration_number"
            ): "UAT 202B",
        }
    )

    return_issue = movement_model.objects.get(
        movement_type="ISSUE",
        **{
            (
                "reservation__work_product_requirement__"
                "work_order__job_card__vehicle__"
                "registration_number"
            ): "UAT 303C",
        },
    )

    work_order = work_order_model.objects.get(
        job_card__vehicle__registration_number="UAT 202B",
    )

    task = work_order.tasks.get()

    require(
        reserve_requirement.inventory_status == "NOT_RESERVED",
        (
            "UAT 101A requirement did not begin "
            f"NOT_RESERVED: "
            f"{reserve_requirement.inventory_status}"
        ),
    )
    require(
        issue_reservation.status == "ACTIVE",
        (f"UAT 202B reservation did not begin ACTIVE: {issue_reservation.status}"),
    )
    require(
        work_order.status == "READY",
        (f"UAT 202B work order did not begin READY: {work_order.status}"),
    )

    return Scenario(
        reserve_requirement_id=reserve_requirement.pk,
        inventory_item_id=inventory_item.pk,
        issue_reservation_id=issue_reservation.pk,
        return_issue_id=return_issue.pk,
        work_order_id=work_order.pk,
        task_id=task.pk,
        initial_issue_quantity=(issue_reservation.quantity_issued),
        initial_return_count=(
            movement_model.objects.filter(
                movement_type="RETURN",
                source_movement_id=return_issue.pk,
            ).count()
        ),
    )


def submit_action_form(
    page: Page,
    *,
    action_path: str,
) -> None:
    """Submit an actual POST-only action form."""
    form = page.locator(f'form[action="{action_path}"]').first

    require(
        form.count() == 1,
        (f"Could not find action form {action_path} at {page.url}."),
    )

    submit = form.locator('button[type="submit"], input[type="submit"]').first

    require(
        submit.count() == 1,
        (f"Could not find the submit control for {action_path}."),
    )

    submit.click()
    page.wait_for_load_state("networkidle")


def test_reserve(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Reserve stock for the seeded unreserved requirement."""
    login(
        page,
        username="senior_technician",
        password="SeniorTechDemo123!",
    )

    response = page.goto(
        full_url(f"/inventory/requirements/{scenario.reserve_requirement_id}/reserve/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Senior Technician reserve-stock page",
    )

    body = page.locator("body").inner_text()

    require(
        "Workshop stock reservation" in body,
        "The stock-reservation page heading was not shown.",
    )
    require(
        "OIL-FILTER-001" in body,
        "The expected oil-filter requirement was not shown.",
    )

    inventory_field = page.locator('[name="inventory_item"]')
    quantity_field = page.locator('[name="quantity"]')

    require(
        inventory_field.count() == 1,
        "The inventory-item field was not shown.",
    )
    require(
        quantity_field.count() == 1,
        "The reservation quantity field was not shown.",
    )

    select_option_containing(
        page,
        field_name="inventory_item",
        expected_text="OIL-FILTER-001",
    )

    quantity_field.fill("1.000")

    submit_form(
        page,
        field_name="inventory_item",
    )

    capture(
        page,
        "UAT-SEN-01-stock-reserved.png",
    )


def test_issue(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Issue stock from the seeded active reservation."""
    response = page.goto(
        full_url(f"/inventory/reservations/{scenario.issue_reservation_id}/issue/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Senior Technician issue-stock page",
    )

    body = page.locator("body").inner_text()

    require(
        "Workshop stock issue" in body,
        "The stock-issue page heading was not shown.",
    )
    require(
        "OIL-FILTER-001" in body,
        "The expected oil-filter reservation was not shown.",
    )

    quantity_field = page.locator('[name="quantity"]')
    notes_field = page.locator('[name="notes"]')

    require(
        quantity_field.count() == 1,
        "The issue quantity field was not shown.",
    )
    require(
        notes_field.count() == 1,
        "The issue notes field was not shown.",
    )

    quantity_field.fill("1.000")
    notes_field.fill(RESERVATION_NOTE)

    submit_form(
        page,
        field_name="quantity",
    )

    capture(
        page,
        "UAT-SEN-02-stock-issued.png",
    )


def test_return(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Return part of the seeded issued quantity."""
    response = page.goto(
        full_url(f"/inventory/movements/{scenario.return_issue_id}/return/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Senior Technician return-stock page",
    )

    body = page.locator("body").inner_text()

    require(
        "Workshop stock return" in body,
        "The stock-return page heading was not shown.",
    )
    require(
        "Return issued stock" in body,
        "The stock-return form was not shown.",
    )
    require(
        "OIL-FILTER-001" in body,
        "The expected returned product was not shown.",
    )

    quantity_field = page.locator('[name="quantity"]')
    notes_field = page.locator('[name="notes"]')

    require(
        quantity_field.count() == 1,
        "The return quantity field was not shown.",
    )
    require(
        notes_field.count() == 1,
        "The return notes field was not shown.",
    )

    quantity_field.fill("0.500")
    notes_field.fill(RETURN_NOTE)

    submit_form(
        page,
        field_name="quantity",
    )

    capture(
        page,
        "UAT-SEN-03-stock-returned.png",
    )


def test_work_order_cycle(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Start, hold, and resume UAT 202B."""
    detail_path = f"/workshop/{scenario.work_order_id}/"

    response = page.goto(
        full_url(detail_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Senior Technician work-order detail",
    )

    start_path = f"/workshop/{scenario.work_order_id}/start/"

    submit_action_form(
        page,
        action_path=start_path,
    )

    require(
        "In progress" in page.locator("body").inner_text(),
        "Work order did not display In progress.",
    )

    capture(
        page,
        "UAT-SEN-04a-work-order-started.png",
    )

    hold_path = f"/workshop/{scenario.work_order_id}/hold/"

    response = page.goto(
        full_url(hold_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Senior Technician hold-work-order page",
    )

    page.locator('[name="reason"]').fill(HOLD_REASON)

    submit_form(
        page,
        field_name="reason",
    )

    require(
        "On hold" in page.locator("body").inner_text(),
        "Work order did not display On hold.",
    )

    capture(
        page,
        "UAT-SEN-04b-work-order-held.png",
    )

    resume_path = f"/workshop/{scenario.work_order_id}/resume/"

    submit_action_form(
        page,
        action_path=resume_path,
    )

    require(
        "In progress" in page.locator("body").inner_text(),
        "Work order did not return to In progress.",
    )

    capture(
        page,
        "UAT-SEN-04c-work-order-resumed.png",
    )


def test_task_note(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Add an append-only technical task note."""
    response = page.goto(
        full_url(f"/workshop/tasks/{scenario.task_id}/notes/new/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Senior Technician task-note page",
    )

    note_type_field = page.locator('[name="note_type"]')
    content_field = page.locator('[name="content"]')

    require(
        note_type_field.count() == 1,
        "The task-note type field was not shown.",
    )
    require(
        content_field.count() == 1,
        "The task-note content field was not shown.",
    )

    note_type_field.select_option(
        label="Technical",
    )
    content_field.fill(TASK_NOTE)

    submit_form(
        page,
        field_name="content",
    )

    expected_detail_path = f"/workshop/{scenario.work_order_id}/"

    require(
        page.url.endswith(expected_detail_path),
        (
            "Task-note submission did not return to "
            f"{expected_detail_path}. Current URL: {page.url}"
        ),
    )

    capture(
        page,
        "UAT-SEN-05-technical-note-added.png",
    )


def test_billing_forbidden(page: Page) -> None:
    """Confirm billing access is forbidden."""
    response = page.goto(
        full_url("/billing/"),
        wait_until="networkidle",
    )

    require(
        response is not None,
        "Billing denial returned no response.",
    )
    require(
        response.status == 403,
        (
            "Senior Technician billing access returned "
            f"HTTP {response.status}; expected 403."
        ),
    )

    capture(
        page,
        "UAT-SEN-06-billing-denied.png",
    )

    RESULTS["UAT-SEN-06"] = CaseResult(
        status="PASS",
        evidence=("`evidence/senior-technician/UAT-SEN-06-billing-denied.png`"),
        notes=("Senior Technician billing access correctly returned HTTP 403."),
    )


def verify_results(
    *,
    scenario: Scenario,
) -> None:
    """Verify all successful changes after Playwright stops."""
    requirement_model = apps.get_model(
        "workshop",
        "WorkProductRequirement",
    )
    reservation_model = apps.get_model(
        "inventory",
        "StockReservation",
    )
    movement_model = apps.get_model(
        "inventory",
        "StockMovement",
    )
    work_order_model = apps.get_model(
        "workshop",
        "WorkOrder",
    )
    note_model = apps.get_model(
        "workshop",
        "WorkTaskNote",
    )

    reserve_requirement = requirement_model.objects.get(
        pk=scenario.reserve_requirement_id,
    )
    created_reservation = reservation_model.objects.get(
        work_product_requirement_id=(scenario.reserve_requirement_id),
        inventory_item_id=scenario.inventory_item_id,
    )

    require(
        reserve_requirement.inventory_status == "RESERVED",
        (
            "UAT 101A requirement status is "
            f"{reserve_requirement.inventory_status}; "
            "expected RESERVED."
        ),
    )
    require(
        created_reservation.quantity_reserved == Decimal("1.000"),
        "Reserved quantity is not 1.000.",
    )
    require(
        created_reservation.reserved_by.username == "senior_technician",
        "Reservation was not created by senior_technician.",
    )

    issue_reservation = reservation_model.objects.get(
        pk=scenario.issue_reservation_id,
    )
    issue_requirement = issue_reservation.work_product_requirement

    require(
        issue_reservation.quantity_issued
        == (scenario.initial_issue_quantity + Decimal("1.000")),
        "Issued quantity did not increase by 1.000.",
    )
    require(
        issue_reservation.status == "PARTIALLY_ISSUED",
        (
            "Issue reservation status is "
            f"{issue_reservation.status}; "
            "expected PARTIALLY_ISSUED."
        ),
    )
    require(
        issue_requirement.inventory_status == "PARTIALLY_ISSUED",
        (
            "Issue requirement status is "
            f"{issue_requirement.inventory_status}; "
            "expected PARTIALLY_ISSUED."
        ),
    )

    issue_movement = movement_model.objects.get(
        reservation_id=scenario.issue_reservation_id,
        notes=RESERVATION_NOTE,
    )

    require(
        issue_movement.quantity == Decimal("1.000"),
        "Issue movement quantity is not 1.000.",
    )
    require(
        issue_movement.created_by.username == "senior_technician",
        "Issue movement was not created by Senior Technician.",
    )

    return_movements = movement_model.objects.filter(
        movement_type="RETURN",
        source_movement_id=scenario.return_issue_id,
    )

    require(
        return_movements.count() == scenario.initial_return_count + 1,
        "Exactly one new stock return was not created.",
    )

    return_movement = return_movements.get(
        notes=RETURN_NOTE,
    )

    require(
        return_movement.quantity == Decimal("0.500"),
        "Return movement quantity is not 0.500.",
    )
    require(
        return_movement.created_by.username == "senior_technician",
        "Return was not created by Senior Technician.",
    )

    work_order = work_order_model.objects.get(
        pk=scenario.work_order_id,
    )

    require(
        work_order.status == "IN_PROGRESS",
        (f"Final work-order status is {work_order.status}; expected IN_PROGRESS."),
    )
    require(
        work_order.started_at is not None,
        "Work order has no start timestamp.",
    )
    require(
        work_order.updated_by is not None,
        "Work order has no updating user.",
    )
    require(
        work_order.updated_by.username == "senior_technician",
        "Work order was not updated by Senior Technician.",
    )

    note = note_model.objects.get(
        work_task_id=scenario.task_id,
        content=TASK_NOTE,
    )

    require(
        note.note_type == "TECHNICAL",
        "Task note type is not TECHNICAL.",
    )
    require(
        note.created_by.username == "senior_technician",
        "Task note was not created by Senior Technician.",
    )

    RESULTS["UAT-SEN-01"] = CaseResult(
        status="PASS",
        evidence=("`evidence/senior-technician/UAT-SEN-01-stock-reserved.png`"),
        notes=("UAT 101A stock was reserved by senior_technician."),
    )
    RESULTS["UAT-SEN-02"] = CaseResult(
        status="PASS",
        evidence=("`evidence/senior-technician/UAT-SEN-02-stock-issued.png`"),
        notes=("UAT 202B reservation became PARTIALLY_ISSUED."),
    )
    RESULTS["UAT-SEN-03"] = CaseResult(
        status="PASS",
        evidence=("`evidence/senior-technician/UAT-SEN-03-stock-returned.png`"),
        notes=("A 0.500 stock return was recorded for UAT 303C."),
    )
    RESULTS["UAT-SEN-04"] = CaseResult(
        status="PASS",
        evidence=(
            "`evidence/senior-technician/"
            "UAT-SEN-04a-work-order-started.png`, "
            "`UAT-SEN-04b-work-order-held.png`, and "
            "`UAT-SEN-04c-work-order-resumed.png`"
        ),
        notes=("UAT 202B completed the start, hold, and resume cycle."),
    )
    RESULTS["UAT-SEN-05"] = CaseResult(
        status="PASS",
        evidence=("`evidence/senior-technician/UAT-SEN-05-technical-note-added.png`"),
        notes=("An append-only TECHNICAL task note was recorded."),
    )


def mark_failure(
    *,
    case_id: str,
    error: Exception,
    page: Page | None,
) -> None:
    """Record one Senior Technician failure."""
    evidence = ""

    if page is not None:
        try:
            if not page.is_closed():
                failure = capture(
                    page,
                    f"{case_id}-failure.png",
                )
                evidence = f"`evidence/senior-technician/{failure.name}`"
        except Exception:
            evidence = ""

    RESULTS[case_id] = CaseResult(
        status="FAIL",
        evidence=evidence,
        issue="AUTOMATED-UAT",
        notes=str(error).replace("|", "/"),
    )


def run() -> int:
    """Execute all Senior Technician UAT cases."""
    clear_evidence()
    reset_ledger_rows()

    call_command(
        "reset_demo_data",
        yes=True,
        verbosity=0,
    )

    scenario = prepare_scenario()

    server = start_server()
    page: Page | None = None
    current_case = "UAT-SEN-01"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
            )
            context = browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
            )
            page = context.new_page()

            current_case = "UAT-SEN-01"
            test_reserve(
                page,
                scenario=scenario,
            )

            current_case = "UAT-SEN-02"
            test_issue(
                page,
                scenario=scenario,
            )

            current_case = "UAT-SEN-03"
            test_return(
                page,
                scenario=scenario,
            )

            current_case = "UAT-SEN-04"
            test_work_order_cycle(
                page,
                scenario=scenario,
            )

            current_case = "UAT-SEN-05"
            test_task_note(
                page,
                scenario=scenario,
            )

            current_case = "UAT-SEN-06"
            test_billing_forbidden(page)

            context.close()
            browser.close()

        current_case = "UAT-SEN-01"
        verify_results(
            scenario=scenario,
        )

    except Exception as error:
        mark_failure(
            case_id=current_case,
            error=error,
            page=page,
        )
        write_results()

        print(
            f"Senior Technician UAT failed in {current_case}: {error}",
            file=sys.stderr,
        )
        print(
            f"Server log: {SERVER_LOG}",
            file=sys.stderr,
        )

        return 1

    finally:
        stop_server(server)

    write_results()

    print("Senior Technician browser UAT passed.")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"Execution ledger: {LEDGER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
