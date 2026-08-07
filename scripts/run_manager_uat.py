"""Execute Manager browser UAT and capture real evidence."""

from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal
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
    download_csv,
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

EVIDENCE_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "manager"
CSV_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "csv"
LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"
SERVER_LOG: Final = Path("/tmp/oyera-manager-uat-server.log")

REPORTS: Final = {
    "customer-finance": (
        "/reports/customer-finance/",
        "/reports/customer-finance/export.csv",
    ),
    "workshop-operations": (
        "/reports/workshop-operations/",
        "/reports/workshop-operations/export.csv",
    ),
    "inventory-activity": (
        "/reports/inventory-activity/",
        "/reports/inventory-activity/export.csv",
    ),
    "purchasing-activity": (
        "/reports/purchasing-activity/",
        "/reports/purchasing-activity/export.csv",
    ),
}

DASHBOARD_PATHS: Final = (
    "/billing/",
    "/customers/",
    "/inventory/",
    "/jobs/",
    "/purchasing/",
    "/reports/",
    "/workshop/",
)

RESULTS: dict[str, CaseResult] = {
    "UAT-MGR-01": CaseResult(),
    "UAT-MGR-02": CaseResult(),
    "UAT-MGR-03": CaseResult(),
    "UAT-MGR-04": CaseResult(),
    "UAT-MGR-05": CaseResult(),
}


def start_server() -> subprocess.Popen[str]:
    """Start a dedicated Manager UAT server."""
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
    """Capture one full-page Manager screenshot."""
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


def clear_manager_evidence() -> None:
    """Remove evidence from an incomplete earlier Manager run."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    CSV_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in EVIDENCE_DIR.glob("UAT-MGR-*"):
        path.unlink(missing_ok=True)

    for path in CSV_DIR.glob("UAT-MGR-02-*"):
        path.unlink(missing_ok=True)


def reset_manager_rows() -> None:
    """Return all Manager ledger rows to NOT RUN."""
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
    """Write actual Manager results into the UAT ledger."""
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


def prepare_scenario_ids() -> tuple[int, int]:
    """Resolve stable IDs before Playwright's event loop starts."""
    purchase_order_model = apps.get_model(
        "purchasing",
        "PurchaseOrder",
    )
    job_card_model = apps.get_model(
        "jobs",
        "JobCard",
    )

    purchase_order = purchase_order_model.objects.get(
        supplier_reference="DEMO-PO-SUBMITTED",
    )
    job_card = job_card_model.objects.get(
        vehicle__registration_number="UAT 505E",
    )

    require(
        purchase_order.status == "SUBMITTED",
        (f"Purchase order did not begin in SUBMITTED status: {purchase_order.status}"),
    )
    require(
        job_card.status != "RELEASED",
        "UAT 505E was already released.",
    )

    return (
        purchase_order.pk,
        job_card.pk,
    )


def test_dashboard(page: Page) -> None:
    """Test Manager authentication and dashboard access."""
    login(
        page,
        username="manager",
        password="ManagerDemo123!",
    )

    for path in DASHBOARD_PATHS:
        require(
            page.locator(f'a[href="{path}"], a[href^="{path}"]').count() > 0,
            f"Manager dashboard is missing {path}.",
        )

    capture(
        page,
        "UAT-MGR-01-dashboard.png",
    )

    RESULTS["UAT-MGR-01"] = CaseResult(
        status="PASS",
        evidence=("`evidence/manager/UAT-MGR-01-dashboard.png`"),
        notes=("Automated Manager login and dashboard verification passed."),
    )


def test_reports(
    page: Page,
    context: BrowserContext,
) -> None:
    """Test all Manager report pages and CSV exports."""
    for name, paths in REPORTS.items():
        report_path, export_path = paths

        response = page.goto(
            full_url(report_path),
            wait_until="networkidle",
        )

        require_response(
            response,
            description=f"{name} Manager report",
        )

        capture(
            page,
            f"UAT-MGR-02-{name}.png",
        )

        download_csv(
            context,
            path=export_path,
            destination=(CSV_DIR / f"UAT-MGR-02-{name}.csv"),
        )

    RESULTS["UAT-MGR-02"] = CaseResult(
        status="PASS",
        evidence=("`evidence/manager/` and `evidence/csv/`"),
        notes=("Four Manager report pages and four CSV exports passed."),
    )


def test_purchase_order_approval(
    page: Page,
    *,
    purchase_order_id: int,
) -> None:
    """Approve the submitted purchase order in Chrome."""
    response = page.goto(
        full_url(f"/purchasing/purchase-orders/{purchase_order_id}/approve/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Manager purchase-order approval",
    )

    require(
        "DEMO-PO-SUBMITTED" in page.locator("body").inner_text(),
        "Expected purchase-order reference was absent.",
    )

    confirmation = page.locator('[name="confirmation"]')
    require(
        confirmation.count() == 1,
        "Approval confirmation checkbox was absent.",
    )

    confirmation.check()
    submit_form(
        page,
        field_name="confirmation",
    )

    capture(
        page,
        "UAT-MGR-03-purchase-order-approved.png",
    )


def test_unpaid_release(
    page: Page,
    *,
    job_card_id: int,
) -> None:
    """Authorise the unpaid UAT 505E vehicle release."""
    response = page.goto(
        full_url(f"/jobs/{job_card_id}/release/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Manager unpaid vehicle release",
    )

    body_text = page.locator("body").inner_text()

    require(
        "UAT 505E" in body_text,
        "The UAT 505E release scenario was not shown.",
    )

    page.locator('[name="final_mileage"]').fill("50500")
    page.locator('[name="final_condition"]').fill(
        "Vehicle ready for controlled UAT release."
    )
    page.locator('[name="received_by_name"]').fill("UAT Manager Receiver")
    page.locator('[name="received_by_contact"]').fill("+256700000505")
    page.locator('[name="handover_notes"]').fill(
        "Keys and documents handed over during UAT."
    )

    override = page.locator('[name="payment_override"]')
    require(
        override.count() == 1,
        "Manager payment-override checkbox was absent.",
    )
    override.check()

    page.locator('[name="payment_override_reason"]').fill(
        "Manager-approved UAT customer credit exception."
    )

    submit_form(
        page,
        field_name="final_mileage",
    )

    capture(
        page,
        "UAT-MGR-04-unpaid-release-approved.png",
    )


def test_admin_forbidden(page: Page) -> None:
    """Confirm Manager cannot enter Django administration."""
    response = page.goto(
        full_url("/admin/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Manager Django admin denial",
    )

    require(
        "/admin/login/" in page.url,
        (f"Manager unexpectedly entered Django administration: {page.url}"),
    )

    capture(
        page,
        "UAT-MGR-05-admin-denied.png",
    )

    RESULTS["UAT-MGR-05"] = CaseResult(
        status="PASS",
        evidence=("`evidence/manager/UAT-MGR-05-admin-denied.png`"),
        notes=("Manager was redirected to the Django admin login page."),
    )


def verify_purchase_order() -> None:
    """Verify purchase-order approval after Playwright stops."""
    purchase_order_model = apps.get_model(
        "purchasing",
        "PurchaseOrder",
    )
    order = purchase_order_model.objects.get(
        supplier_reference="DEMO-PO-SUBMITTED",
    )

    require(
        order.status == "APPROVED",
        (f"Purchase order remained {order.status}; expected APPROVED."),
    )
    require(
        order.approved_by is not None,
        "Purchase order has no approving Manager.",
    )
    require(
        order.approved_by.username == "manager",
        (f"Purchase order was approved by {order.approved_by.username!r}."),
    )

    RESULTS["UAT-MGR-03"] = CaseResult(
        status="PASS",
        evidence=("`evidence/manager/UAT-MGR-03-purchase-order-approved.png`"),
        notes=("DEMO-PO-SUBMITTED was approved by manager."),
    )


def verify_unpaid_release(
    *,
    job_card_id: int,
) -> None:
    """Verify the stored unpaid-release override."""
    vehicle_release_model = apps.get_model(
        "jobs",
        "VehicleRelease",
    )
    job_card_model = apps.get_model(
        "jobs",
        "JobCard",
    )

    release = vehicle_release_model.objects.get(
        job_card_id=job_card_id,
    )
    job_card = job_card_model.objects.get(
        pk=job_card_id,
    )

    require(
        job_card.status == "RELEASED",
        (f"UAT 505E job status is {job_card.status}, not RELEASED."),
    )
    require(
        release.payment_override is True,
        "The release does not contain a payment override.",
    )
    require(
        release.payment_override_reason
        == ("Manager-approved UAT customer credit exception."),
        "The stored override reason is incorrect.",
    )
    require(
        release.payment_override_by is not None,
        "No payment-override approver was recorded.",
    )
    require(
        release.payment_override_by.username == "manager",
        "The payment override was not approved by manager.",
    )
    require(
        release.released_by.username == "manager",
        "The vehicle was not released by manager.",
    )
    require(
        release.outstanding_amount_snapshot > Decimal("0.00"),
        "The unpaid balance was not preserved.",
    )
    require(
        release.received_by_name == "UAT Manager Receiver",
        "The receiver name was not stored correctly.",
    )

    RESULTS["UAT-MGR-04"] = CaseResult(
        status="PASS",
        evidence=("`evidence/manager/UAT-MGR-04-unpaid-release-approved.png`"),
        notes=(
            "UAT 505E was released with a Manager "
            "payment override and outstanding balance."
        ),
    )


def mark_failure(
    *,
    case_id: str,
    error: Exception,
    page: Page | None,
) -> None:
    """Record one Manager automation failure."""
    evidence = ""

    if page is not None:
        try:
            if not page.is_closed():
                failure = capture(
                    page,
                    f"{case_id}-failure.png",
                )
                evidence = f"`evidence/manager/{failure.name}`"
        except Exception:
            evidence = ""

    RESULTS[case_id] = CaseResult(
        status="FAIL",
        evidence=evidence,
        issue="AUTOMATED-UAT",
        notes=str(error).replace("|", "/"),
    )


def run() -> int:
    """Execute all Manager UAT cases."""
    clear_manager_evidence()
    reset_manager_rows()

    call_command(
        "reset_demo_data",
        yes=True,
        verbosity=0,
    )

    purchase_order_id, job_card_id = prepare_scenario_ids()

    server = start_server()
    page: Page | None = None
    current_case = "UAT-MGR-01"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
            )
            context = browser.new_context(
                accept_downloads=True,
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
            )
            page = context.new_page()

            current_case = "UAT-MGR-01"
            test_dashboard(page)

            current_case = "UAT-MGR-02"
            test_reports(
                page,
                context,
            )

            current_case = "UAT-MGR-03"
            test_purchase_order_approval(
                page,
                purchase_order_id=purchase_order_id,
            )

            current_case = "UAT-MGR-04"
            test_unpaid_release(
                page,
                job_card_id=job_card_id,
            )

            current_case = "UAT-MGR-05"
            test_admin_forbidden(page)

            context.close()
            browser.close()

        current_case = "UAT-MGR-03"
        verify_purchase_order()

        current_case = "UAT-MGR-04"
        verify_unpaid_release(
            job_card_id=job_card_id,
        )

    except Exception as error:
        mark_failure(
            case_id=current_case,
            error=error,
            page=page,
        )
        write_results()

        print(
            f"Manager UAT failed in {current_case}: {error}",
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

    print("Manager browser UAT passed.")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"CSV directory: {CSV_DIR}")
    print(f"Execution ledger: {LEDGER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
