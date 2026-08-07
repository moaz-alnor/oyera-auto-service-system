"""Execute Administrator browser UAT and capture real evidence."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Final

import django
from django.apps import apps
from django.core.management import call_command
from playwright.sync_api import (
    BrowserContext,
    Page,
    Response,
    sync_playwright,
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

django.setup()

ROOT_DIR: Final = Path(__file__).resolve().parents[1]
BASE_URL: Final = "http://127.0.0.1:8000"

EVIDENCE_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "administrator"
CSV_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "csv"
LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"

SERVER_LOG: Final = Path("/tmp/oyera-administrator-uat-server.log")

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
    "/admin/",
    "/billing/",
    "/customers/",
    "/inventory/",
    "/jobs/",
    "/products/",
    "/purchasing/",
    "/quotations/",
    "/reports/",
    "/services/",
    "/vehicles/",
    "/workshop/",
)


@dataclass
class CaseResult:
    """Store one UAT result."""

    status: str = "NOT RUN"
    evidence: str = ""
    issue: str = ""
    notes: str = ""


RESULTS: dict[str, CaseResult] = {
    "UAT-ADM-01": CaseResult(),
    "UAT-ADM-02": CaseResult(),
    "UAT-ADM-03": CaseResult(),
    "UAT-ADM-04": CaseResult(),
}


def require(
    condition: bool,
    message: str,
) -> None:
    """Raise a readable UAT failure."""
    if not condition:
        raise AssertionError(message)


def wait_for_server(
    *,
    timeout_seconds: int = 45,
) -> None:
    """Wait until the local liveness endpoint responds."""
    deadline = time.monotonic() + timeout_seconds
    url = f"{BASE_URL}/health/live/"

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                url,
                timeout=2,
            ) as response:
                if response.status == 200:
                    return
        except (
            urllib.error.URLError,
            TimeoutError,
        ):
            pass

        time.sleep(1)

    raise RuntimeError("The UAT server did not become ready.")


def start_server() -> subprocess.Popen[str]:
    """Start a dedicated no-reload development server."""
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

    try:
        wait_for_server()
    except Exception:
        process.terminate()
        process.wait(timeout=10)
        raise

    return process


def stop_server(
    process: subprocess.Popen[str],
) -> None:
    """Stop the dedicated UAT server."""
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def full_url(path: str) -> str:
    """Return one absolute local URL."""
    return f"{BASE_URL}{path}"


def require_response(
    response: Response | None,
    *,
    expected_status: int = 200,
    description: str,
) -> None:
    """Require one browser navigation response."""
    require(
        response is not None,
        f"{description} produced no HTTP response.",
    )

    require(
        response.status == expected_status,
        (f"{description} returned HTTP {response.status}; expected {expected_status}."),
    )


def capture(
    page: Page,
    filename: str,
) -> Path:
    """Capture a full-page PNG screenshot."""
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


def form_with_field(
    page: Page,
    field_name: str,
):
    """Return the first form containing a field."""
    form = page.locator(f'form:has([name="{field_name}"])').first

    require(
        form.count() == 1,
        (f"No form containing field {field_name!r} was found at {page.url}."),
    )

    return form


def submit_form(
    page: Page,
    *,
    field_name: str,
) -> None:
    """Submit a form and wait for the resulting page."""
    form = form_with_field(
        page,
        field_name,
    )

    submit = form.locator('button[type="submit"], input[type="submit"]').last

    if submit.count() == 1:
        submit.click()
    else:
        form.evaluate("(form) => form.submit()")

    page.wait_for_load_state("networkidle")


def login(
    page: Page,
    *,
    username: str,
    password: str,
) -> None:
    """Authenticate through the actual login page."""
    response = page.goto(
        full_url("/accounts/login/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Login page",
    )

    page.locator('[name="username"]').fill(username)
    page.locator('[name="password"]').fill(password)

    submit_form(
        page,
        field_name="username",
    )

    require(
        page.url.rstrip("/") == BASE_URL,
        (f"Login did not finish on the dashboard. Current URL: {page.url}"),
    )


def clear_administrator_evidence() -> None:
    """Remove evidence left by an incomplete earlier run."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    CSV_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for evidence_path in EVIDENCE_DIR.glob("UAT-ADM-*"):
        evidence_path.unlink(
            missing_ok=True,
        )

    for csv_path in CSV_DIR.glob("UAT-ADM-03-*"):
        csv_path.unlink(
            missing_ok=True,
        )


def reset_administrator_rows() -> None:
    """Remove the invalid manually recorded PASS results."""
    require(
        LEDGER_PATH.exists(),
        (f"The UAT execution ledger was not found: {LEDGER_PATH}"),
    )

    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()

    updated_lines: list[str] = []

    for line in lines:
        case_id = next(
            (case for case in RESULTS if line.startswith(f"| {case} |")),
            None,
        )

        if case_id is None:
            updated_lines.append(line)
            continue

        updated_lines.append(f"| {case_id} | NOT RUN |  |  |  |")

    LEDGER_PATH.write_text(
        "\n".join(updated_lines) + "\n",
        encoding="utf-8",
    )


def write_results() -> None:
    """Write actual automated results into the ledger."""
    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()

    updated_lines: list[str] = []

    for line in lines:
        case_id = next(
            (case for case in RESULTS if line.startswith(f"| {case} |")),
            None,
        )

        if case_id is None:
            updated_lines.append(line)
            continue

        result = RESULTS[case_id]

        updated_lines.append(
            f"| {case_id} "
            f"| {result.status} "
            f"| {result.evidence} "
            f"| {result.issue} "
            f"| {result.notes} |"
        )

    LEDGER_PATH.write_text(
        "\n".join(updated_lines) + "\n",
        encoding="utf-8",
    )


def test_dashboard(
    page: Page,
) -> None:
    """Test Administrator login and dashboard navigation."""
    login(
        page,
        username="admin",
        password="AdminDemo123!",
    )

    for expected_path in DASHBOARD_PATHS:
        link_count = page.locator(
            f'a[href="{expected_path}"], a[href^="{expected_path}"]'
        ).count()

        require(
            link_count > 0,
            (f"Administrator dashboard is missing a link for {expected_path}."),
        )

    capture(
        page,
        "UAT-ADM-01-dashboard.png",
    )

    RESULTS["UAT-ADM-01"] = CaseResult(
        status="PASS",
        evidence=("`evidence/administrator/UAT-ADM-01-dashboard.png`"),
        notes=("Automated Chrome login and dashboard navigation verification passed."),
    )


def test_django_admin(
    page: Page,
) -> None:
    """Test Django administration access."""
    response = page.goto(
        full_url("/admin/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Django administration",
    )

    require(
        "/admin/login/" not in page.url,
        "Administrator was redirected to admin login.",
    )

    body_text = page.locator("body").inner_text()

    require(
        ("Site administration" in body_text or "Django administration" in body_text),
        "Django administration index was not visible.",
    )

    capture(
        page,
        "UAT-ADM-02-django-admin.png",
    )

    RESULTS["UAT-ADM-02"] = CaseResult(
        status="PASS",
        evidence=("`evidence/administrator/UAT-ADM-02-django-admin.png`"),
        notes=("Django staff and superuser access passed."),
    )


def download_csv(
    context: BrowserContext,
    *,
    path: str,
    destination: Path,
) -> None:
    """Download and validate one authenticated CSV."""
    response = context.request.get(
        full_url(path),
    )

    require(
        response.ok,
        (f"CSV request {path} returned HTTP {response.status}."),
    )

    content_type = response.headers.get(
        "content-type",
        "",
    )

    require(
        "csv" in content_type.lower(),
        (f"{path} returned unexpected Content-Type: {content_type}"),
    )

    data = response.body()

    require(
        len(data) > 0,
        f"{path} returned an empty CSV.",
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_bytes(data)

    try:
        decoded_csv = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AssertionError(f"{destination.name} is not valid UTF-8 CSV.") from error

    rows = list(
        csv.reader(
            StringIO(decoded_csv),
        )
    )
    populated_rows = [row for row in rows if any(cell.strip() for cell in row)]

    require(
        bool(populated_rows),
        f"{destination.name} contains no populated CSV rows.",
    )

    require(
        any(len(row) >= 2 for row in populated_rows),
        (f"{destination.name} contains no structured multi-column rows."),
    )


def test_reports(
    page: Page,
    context: BrowserContext,
) -> None:
    """Test all Administrator reports and CSV exports."""
    for report_name, paths in REPORTS.items():
        report_path, export_path = paths

        response = page.goto(
            full_url(report_path),
            wait_until="networkidle",
        )

        require_response(
            response,
            description=(f"{report_name} report"),
        )

        capture(
            page,
            f"UAT-ADM-03-{report_name}.png",
        )

        download_csv(
            context,
            path=export_path,
            destination=(CSV_DIR / f"UAT-ADM-03-{report_name}.csv"),
        )

    RESULTS["UAT-ADM-03"] = CaseResult(
        status="PASS",
        evidence=("`evidence/administrator/` and `evidence/csv/`"),
        notes=("Four report pages and four authenticated CSV exports passed."),
    )


def get_submitted_purchase_order_id() -> int:
    """Return the submitted demo order before Playwright starts."""
    purchase_order_model = apps.get_model(
        "purchasing",
        "PurchaseOrder",
    )
    order = purchase_order_model.objects.get(
        supplier_reference="DEMO-PO-SUBMITTED",
    )

    require(
        order.status == "SUBMITTED",
        (f"Purchase order did not begin in SUBMITTED status: {order.status}"),
    )

    return order.pk


def test_purchase_order_approval(
    page: Page,
    *,
    order_id: int,
) -> None:
    """Submit approval through the real browser interface."""
    response = page.goto(
        full_url(f"/purchasing/purchase-orders/{order_id}/approve/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Purchase-order approval page",
    )

    body_text = page.locator("body").inner_text()

    require(
        "DEMO-PO-SUBMITTED" in body_text,
        ("The expected purchase-order reference was not shown."),
    )

    confirmation = page.locator('[name="confirmation"]')

    require(
        confirmation.count() == 1,
        ("Purchase-order confirmation checkbox was not found."),
    )

    confirmation.check()

    submit_form(
        page,
        field_name="confirmation",
    )

    capture(
        page,
        "UAT-ADM-04-purchase-order-approved.png",
    )


def verify_purchase_order_approval() -> None:
    """Verify approval after the Playwright event loop has stopped."""
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
        "Purchase order has no approving user.",
    )

    require(
        order.approved_by.username == "admin",
        (f"Purchase order was approved by {order.approved_by.username!r}, not admin."),
    )

    require(
        order.approved_at is not None,
        "Purchase order has no approval timestamp.",
    )

    RESULTS["UAT-ADM-04"] = CaseResult(
        status="PASS",
        evidence=("`evidence/administrator/UAT-ADM-04-purchase-order-approved.png`"),
        notes=(
            "DEMO-PO-SUBMITTED changed to APPROVED with administrator audit evidence."
        ),
    )


def mark_failure(
    *,
    current_case: str,
    error: Exception,
    page: Page | None,
) -> None:
    """Record the active case as failed."""
    evidence = ""

    if page is not None:
        try:
            failure_path = capture(
                page,
                f"{current_case}-failure.png",
            )
            evidence = f"`evidence/administrator/{failure_path.name}`"
        except Exception:
            evidence = ""

    RESULTS[current_case] = CaseResult(
        status="FAIL",
        evidence=evidence,
        issue="AUTOMATED-UAT",
        notes=str(error).replace("|", "/"),
    )


def run(
    *,
    headed: bool,
) -> int:
    """Execute all Administrator browser cases."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    CSV_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    clear_administrator_evidence()
    reset_administrator_rows()

    call_command(
        "reset_demo_data",
        yes=True,
        verbosity=0,
    )

    purchase_order_id = get_submitted_purchase_order_id()

    server = start_server()
    page: Page | None = None
    current_case = "UAT-ADM-01"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=not headed,
            )

            context = browser.new_context(
                accept_downloads=True,
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
            )

            page = context.new_page()

            current_case = "UAT-ADM-01"
            test_dashboard(page)

            current_case = "UAT-ADM-02"
            test_django_admin(page)

            current_case = "UAT-ADM-03"
            test_reports(
                page,
                context,
            )

            current_case = "UAT-ADM-04"
            test_purchase_order_approval(
                page,
                order_id=purchase_order_id,
            )

            context.close()
            browser.close()

        verify_purchase_order_approval()

    except Exception as error:
        mark_failure(
            current_case=current_case,
            error=error,
            page=page,
        )
        write_results()

        print(
            f"Administrator UAT failed in {current_case}: {error}",
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

    print("Administrator browser UAT passed.")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"CSV directory: {CSV_DIR}")
    print(f"Execution ledger: {LEDGER_PATH}")

    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description=("Run Administrator browser UAT and capture evidence.")
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help=("Show Google Chrome while the automation runs."),
    )

    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()

    raise SystemExit(
        run(
            headed=arguments.headed,
        )
    )
