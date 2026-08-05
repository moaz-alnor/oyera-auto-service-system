"""Execute Technician browser UAT and capture real evidence."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import django
from django.apps import apps
from django.core.management import call_command
from playwright.sync_api import (
    BrowserContext,
    Page,
    sync_playwright,
)
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

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

django.setup()

ROOT_DIR: Final = Path(__file__).resolve().parents[1]

EVIDENCE_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "technician"
LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"
SERVER_LOG: Final = Path("/tmp/oyera-technician-uat-server.log")

BLOCK_REASON: Final = "UAT blocked while awaiting replacement seal."
COMPLETION_NOTES: Final = (
    "Completed oil and filter service, checked for leaks, "
    "and verified normal operation during UAT."
)

RESULTS: dict[str, CaseResult] = {
    "UAT-TEC-01": CaseResult(),
    "UAT-TEC-02": CaseResult(),
    "UAT-TEC-03": CaseResult(),
    "UAT-TEC-04": CaseResult(),
    "UAT-TEC-05": CaseResult(),
}


@dataclass(frozen=True)
class Scenario:
    """Store the assigned Technician task scenarios."""

    block_work_order_id: int
    block_task_id: int
    review_work_order_id: int
    review_task_id: int


def start_server() -> subprocess.Popen[str]:
    """Start a dedicated Technician UAT server."""
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
    """Capture one full-page Technician screenshot."""
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
    """Remove evidence from an incomplete Technician run."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in EVIDENCE_DIR.glob("UAT-TEC-*"):
        path.unlink(missing_ok=True)


def reset_ledger_rows() -> None:
    """Return all Technician ledger rows to NOT RUN."""
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
    """Write actual Technician results into the ledger."""
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
    """Resolve assigned tasks before Playwright starts."""
    work_order_model = apps.get_model(
        "workshop",
        "WorkOrder",
    )
    assignment_model = apps.get_model(
        "workshop",
        "TechnicianAssignment",
    )

    block_order = work_order_model.objects.get(
        job_card__vehicle__registration_number="UAT 202B",
    )
    review_order = work_order_model.objects.get(
        job_card__vehicle__registration_number="UAT 303C",
    )

    block_task = block_order.tasks.get()
    review_task = review_order.tasks.get()

    block_assignment = assignment_model.objects.get(
        work_task=block_task,
        technician__username="technician",
        is_active=True,
    )
    review_assignment = assignment_model.objects.get(
        work_task=review_task,
        technician__username="technician",
        is_active=True,
    )

    require(
        block_order.status == "READY",
        (f"UAT 202B work order did not begin READY: {block_order.status}"),
    )
    require(
        review_order.status == "READY",
        (f"UAT 303C work order did not begin READY: {review_order.status}"),
    )
    require(
        block_task.status == "ASSIGNED",
        (f"UAT 202B task did not begin ASSIGNED: {block_task.status}"),
    )
    require(
        review_task.status == "ASSIGNED",
        (f"UAT 303C task did not begin ASSIGNED: {review_task.status}"),
    )
    require(
        block_assignment.status == "ASSIGNED",
        "UAT 202B Technician assignment is not ASSIGNED.",
    )
    require(
        review_assignment.status == "ASSIGNED",
        "UAT 303C Technician assignment is not ASSIGNED.",
    )

    return Scenario(
        block_work_order_id=block_order.pk,
        block_task_id=block_task.pk,
        review_work_order_id=review_order.pk,
        review_task_id=review_task.pk,
    )


def submit_action_form(
    page: Page,
    *,
    action_path: str,
) -> None:
    """Submit one real POST-only application action."""
    form = page.locator(f'form[action="{action_path}"]').first

    require(
        form.count() == 1,
        (f"Could not find action form {action_path} at {page.url}."),
    )

    submit = form.locator('button[type="submit"], input[type="submit"]').first

    require(
        submit.count() == 1,
        (f"Could not find a submit control for {action_path}."),
    )

    submit.click()
    page.wait_for_load_state("networkidle")


def start_work_order_as_admin(
    page: Page,
    *,
    work_order_id: int,
) -> None:
    """Start a ready work order through the Administrator UI."""
    detail_path = f"/workshop/{work_order_id}/"

    response = page.goto(
        full_url(detail_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Administrator work-order preparation",
    )

    submit_action_form(
        page,
        action_path=(f"/workshop/{work_order_id}/start/"),
    )

    require(
        "In progress" in page.locator("body").inner_text(),
        (f"Work order {work_order_id} did not display In progress."),
    )


def prepare_work_orders_in_browser(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Start both assigned work orders as Administrator."""
    login(
        page,
        username="admin",
        password="AdminDemo123!",
    )

    start_work_order_as_admin(
        page,
        work_order_id=scenario.block_work_order_id,
    )
    start_work_order_as_admin(
        page,
        work_order_id=scenario.review_work_order_id,
    )


def test_dashboard(page: Page) -> None:
    """Test Technician authentication and navigation."""
    login(
        page,
        username="technician",
        password="TechnicianDemo123!",
    )

    required_paths = (
        "/workshop/",
        "/jobs/",
        "/inventory/",
        "/products/",
        "/services/",
        "/vehicles/",
    )

    for path in required_paths:
        require(
            page.locator(f'a[href="{path}"], a[href^="{path}"]').count() > 0,
            f"Technician dashboard is missing {path}.",
        )

    require(
        page.locator('a[href="/billing/"], a[href^="/billing/"]').count() == 0,
        "Technician dashboard unexpectedly shows billing.",
    )
    require(
        page.locator('a[href="/reports/"], a[href^="/reports/"]').count() == 0,
        "Technician dashboard unexpectedly shows reports.",
    )

    capture(
        page,
        "UAT-TEC-01-dashboard.png",
    )

    RESULTS["UAT-TEC-01"] = CaseResult(
        status="PASS",
        evidence=("`evidence/technician/UAT-TEC-01-dashboard.png`"),
        notes=("Technician login and assigned-work navigation passed."),
    )


def post_authenticated_action(
    context: BrowserContext,
    *,
    action_path: str,
    referer_path: str,
    description: str,
) -> None:
    """Submit an authenticated POST-only workshop action."""
    csrf_token = get_csrf_token(context)

    response = context.request.post(
        full_url(action_path),
        headers={
            "X-CSRFToken": csrf_token,
            "Referer": full_url(referer_path),
        },
        max_redirects=0,
    )

    require(
        response.status == 302,
        (f"{description} returned HTTP {response.status}; expected 302."),
    )


def test_start_and_block(
    page: Page,
    context: BrowserContext,
    *,
    scenario: Scenario,
) -> None:
    """Start and block the assigned UAT 202B task."""
    detail_path = f"/workshop/{scenario.block_work_order_id}/"
    start_path = f"/workshop/tasks/{scenario.block_task_id}/start/"
    block_path = f"/workshop/tasks/{scenario.block_task_id}/block/"

    response = page.goto(
        full_url(detail_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Technician UAT 202B work order",
    )

    post_authenticated_action(
        context,
        action_path=start_path,
        referer_path=detail_path,
        description="Technician task start",
    )

    response = page.goto(
        full_url(block_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Technician task-block page",
    )

    reason_field = page.locator('[name="reason"]')

    require(
        reason_field.count() == 1,
        "The task-block reason field was not shown.",
    )

    reason_field.fill(BLOCK_REASON)

    submit_form(
        page,
        field_name="reason",
    )

    capture(
        page,
        "UAT-TEC-02-task-blocked.png",
    )


def test_submit_for_review(
    page: Page,
    context: BrowserContext,
    *,
    scenario: Scenario,
) -> None:
    """Start UAT 303C and submit it for review."""
    detail_path = f"/workshop/{scenario.review_work_order_id}/"
    start_path = f"/workshop/tasks/{scenario.review_task_id}/start/"
    review_path = f"/workshop/tasks/{scenario.review_task_id}/review/"

    response = page.goto(
        full_url(detail_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Technician UAT 303C work order",
    )

    post_authenticated_action(
        context,
        action_path=start_path,
        referer_path=detail_path,
        description="Technician review-task start",
    )

    response = page.goto(
        full_url(review_path),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Technician task-review form",
    )

    completion_notes_field = page.locator('[name="completion_notes"]')

    require(
        completion_notes_field.count() == 1,
        "The completion-notes field was not shown.",
    )

    completion_notes_field.fill(COMPLETION_NOTES)

    submit_form(
        page,
        field_name="completion_notes",
    )

    capture(
        page,
        "UAT-TEC-03-task-awaiting-review.png",
    )


def get_csrf_token(
    context: BrowserContext,
) -> str:
    """Return the current browser CSRF cookie."""
    cookies = context.cookies()

    for cookie in cookies:
        if cookie["name"] == "csrftoken":
            return cookie["value"]

    raise AssertionError("The Technician browser has no CSRF cookie.")


def test_self_approval_rejected(
    page: Page,
    context: BrowserContext,
    *,
    scenario: Scenario,
) -> None:
    """Attempt task approval as the submitting Technician."""
    detail_path = f"/workshop/{scenario.review_work_order_id}/"
    approval_path = f"/workshop/tasks/{scenario.review_task_id}/approve/"

    csrf_token = get_csrf_token(context)

    response = context.request.post(
        full_url(approval_path),
        headers={
            "X-CSRFToken": csrf_token,
            "Referer": full_url(detail_path),
        },
        max_redirects=0,
    )

    require(
        response.status
        in {
            302,
            403,
        },
        (
            "Technician self-approval returned HTTP "
            f"{response.status}; expected 302 or 403."
        ),
    )

    page_response = page.goto(
        full_url(detail_path),
        wait_until="networkidle",
    )

    require_response(
        page_response,
        description="Technician approval rejection result",
    )

    capture(
        page,
        "UAT-TEC-04-approval-rejected.png",
    )


def test_reports_forbidden(page: Page) -> None:
    """Confirm Technician report access is forbidden."""
    response = page.goto(
        full_url("/reports/"),
        wait_until="networkidle",
    )

    require(
        response is not None,
        "Technician reports denial returned no response.",
    )
    require(
        response.status == 403,
        (f"Technician reports access returned HTTP {response.status}; expected 403."),
    )

    capture(
        page,
        "UAT-TEC-05-reports-denied.png",
    )

    RESULTS["UAT-TEC-05"] = CaseResult(
        status="PASS",
        evidence=("`evidence/technician/UAT-TEC-05-reports-denied.png`"),
        notes=("Technician reports access correctly returned HTTP 403."),
    )


def verify_results(
    *,
    scenario: Scenario,
) -> None:
    """Verify Technician changes after Playwright stops."""
    work_order_model = apps.get_model(
        "workshop",
        "WorkOrder",
    )
    task_model = apps.get_model(
        "workshop",
        "WorkTask",
    )
    assignment_model = apps.get_model(
        "workshop",
        "TechnicianAssignment",
    )

    block_order = work_order_model.objects.get(
        pk=scenario.block_work_order_id,
    )
    review_order = work_order_model.objects.get(
        pk=scenario.review_work_order_id,
    )

    block_task = task_model.objects.get(
        pk=scenario.block_task_id,
    )
    review_task = task_model.objects.get(
        pk=scenario.review_task_id,
    )

    block_assignment = assignment_model.objects.get(
        work_task=block_task,
        technician__username="technician",
        is_active=True,
    )
    review_assignment = assignment_model.objects.get(
        work_task=review_task,
        technician__username="technician",
        is_active=True,
    )

    require(
        block_order.status == "IN_PROGRESS",
        (f"UAT 202B work-order status is {block_order.status}; expected IN_PROGRESS."),
    )
    require(
        block_task.status == "BLOCKED",
        (f"UAT 202B task status is {block_task.status}; expected BLOCKED."),
    )
    require(
        block_task.blocked_reason == BLOCK_REASON,
        "The Technician block reason was not stored.",
    )
    require(
        block_task.updated_by.username == "technician",
        "UAT 202B task was not updated by technician.",
    )
    require(
        block_assignment.status == "IN_PROGRESS",
        (
            "UAT 202B assignment status is "
            f"{block_assignment.status}; "
            "expected IN_PROGRESS."
        ),
    )

    require(
        review_order.status == "AWAITING_REVIEW",
        (
            "UAT 303C work-order status is "
            f"{review_order.status}; "
            "expected AWAITING_REVIEW."
        ),
    )
    require(
        review_task.status == "AWAITING_REVIEW",
        (f"UAT 303C task status is {review_task.status}; expected AWAITING_REVIEW."),
    )
    require(
        review_task.completion_notes == COMPLETION_NOTES,
        "Technician completion notes were not stored.",
    )
    require(
        review_task.updated_by.username == "technician",
        "UAT 303C task was not updated by technician.",
    )
    require(
        review_assignment.status == "IN_PROGRESS",
        (
            "UAT 303C assignment status is "
            f"{review_assignment.status}; "
            "expected IN_PROGRESS."
        ),
    )

    # The self-approval attempt must not complete the task.
    require(
        review_task.status != "COMPLETED",
        "Technician was incorrectly allowed to self-approve.",
    )

    RESULTS["UAT-TEC-02"] = CaseResult(
        status="PASS",
        evidence=("`evidence/technician/UAT-TEC-02-task-blocked.png`"),
        notes=(
            "Assigned UAT 202B task was started and blocked with an auditable reason."
        ),
    )
    RESULTS["UAT-TEC-03"] = CaseResult(
        status="PASS",
        evidence=("`evidence/technician/UAT-TEC-03-task-awaiting-review.png`"),
        notes=("Assigned UAT 303C task was submitted with completion evidence."),
    )
    RESULTS["UAT-TEC-04"] = CaseResult(
        status="PASS",
        evidence=("`evidence/technician/UAT-TEC-04-approval-rejected.png`"),
        notes=(
            "Technician self-approval was rejected; the task remained AWAITING_REVIEW."
        ),
    )


def mark_failure(
    *,
    case_id: str,
    error: Exception,
    page: Page | None,
) -> None:
    """Record one Technician automation failure."""
    evidence = ""

    if page is not None:
        try:
            if not page.is_closed():
                failure = capture(
                    page,
                    f"{case_id}-failure.png",
                )
                evidence = f"`evidence/technician/{failure.name}`"
        except Exception:
            evidence = ""

    RESULTS[case_id] = CaseResult(
        status="FAIL",
        evidence=evidence,
        issue="AUTOMATED-UAT",
        notes=str(error).replace("|", "/"),
    )


def run() -> int:
    """Execute all Technician UAT cases."""
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
    current_case = "UAT-TEC-01"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
            )

            admin_context = browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
            )
            admin_page = admin_context.new_page()

            prepare_work_orders_in_browser(
                admin_page,
                scenario=scenario,
            )

            admin_context.close()

            technician_context = browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
            )
            page = technician_context.new_page()

            current_case = "UAT-TEC-01"
            test_dashboard(page)

            current_case = "UAT-TEC-02"
            test_start_and_block(
                page,
                technician_context,
                scenario=scenario,
            )

            current_case = "UAT-TEC-03"
            test_submit_for_review(
                page,
                technician_context,
                scenario=scenario,
            )

            current_case = "UAT-TEC-04"
            test_self_approval_rejected(
                page,
                technician_context,
                scenario=scenario,
            )

            current_case = "UAT-TEC-05"
            test_reports_forbidden(page)

            technician_context.close()
            browser.close()

        current_case = "UAT-TEC-02"
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
            f"Technician UAT failed in {current_case}: {error}",
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

    print("Technician browser UAT passed.")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"Execution ledger: {LEDGER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
