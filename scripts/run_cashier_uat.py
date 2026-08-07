"""Execute Cashier browser UAT and capture real evidence."""

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
from django.db.models import Sum
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

EVIDENCE_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "cashier"
CSV_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "csv"
LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"
SERVER_LOG: Final = Path("/tmp/oyera-cashier-uat-server.log")

CUSTOMER_PAYMENT_REFERENCE: Final = "UAT-CUSTOMER-PAY-001"
SUPPLIER_PAYMENT_REFERENCE: Final = "UAT-SUPPLIER-PAY-001"
CUSTOMER_PAYMENT_NOTES: Final = "Partial customer payment recorded during UAT."
SUPPLIER_PAYMENT_NOTES: Final = "Partial supplier payment recorded during UAT."

CUSTOMER_PAYMENT_AMOUNT: Final = Decimal("10000.00")
SUPPLIER_PAYMENT_AMOUNT: Final = Decimal("25000.00")

REPORTS: Final = {
    "customer-finance": (
        "/reports/customer-finance/",
        "/reports/customer-finance/export.csv",
    ),
    "purchasing-activity": (
        "/reports/purchasing-activity/",
        "/reports/purchasing-activity/export.csv",
    ),
}

RESULTS: dict[str, CaseResult] = {
    "UAT-CAS-01": CaseResult(),
    "UAT-CAS-02": CaseResult(),
    "UAT-CAS-03": CaseResult(),
    "UAT-CAS-04": CaseResult(),
    "UAT-CAS-05": CaseResult(),
    "UAT-CAS-06": CaseResult(),
}


@dataclass(frozen=True)
class Scenario:
    """Store Cashier UAT IDs and starting balances."""

    customer_invoice_id: int
    supplier_invoice_id: int
    paid_release_job_id: int
    initial_customer_payment_total: Decimal
    initial_supplier_payment_total: Decimal


def start_server() -> subprocess.Popen[str]:
    """Start a dedicated Cashier UAT server."""
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
    """Capture one full-page Cashier screenshot."""
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


def markdown_row(
    values: list[str],
) -> str:
    """Create one consistently spaced Markdown row."""
    return "| " + " | ".join(values) + " |"


def clear_evidence() -> None:
    """Remove evidence from an incomplete Cashier run."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    CSV_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in EVIDENCE_DIR.glob("UAT-CAS-*"):
        path.unlink(missing_ok=True)

    for path in CSV_DIR.glob("UAT-CAS-*"):
        path.unlink(missing_ok=True)


def reset_ledger_rows() -> None:
    """Return all Cashier ledger rows to NOT RUN."""
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

        updated.append(
            markdown_row(
                [
                    case_id,
                    "NOT RUN",
                    "",
                    "",
                    "",
                ]
            )
        )

    LEDGER_PATH.write_text(
        "\n".join(updated) + "\n",
        encoding="utf-8",
    )


def write_results() -> None:
    """Write actual Cashier results into the ledger."""
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
            markdown_row(
                [
                    case_id,
                    result.status,
                    result.evidence,
                    result.issue,
                    result.notes,
                ]
            )
        )

    LEDGER_PATH.write_text(
        "\n".join(updated) + "\n",
        encoding="utf-8",
    )


def posted_payment_total(
    model,
    *,
    relationship_filter: dict[str, int],
) -> Decimal:
    """Return the total value of active posted payments."""
    result = model.objects.filter(
        status="POSTED",
        **relationship_filter,
    ).aggregate(total=Sum("amount"))["total"]

    return result or Decimal("0.00")


def prepare_scenario() -> Scenario:
    """Resolve Cashier scenarios before Playwright starts."""
    invoice_model = apps.get_model(
        "billing",
        "Invoice",
    )
    payment_model = apps.get_model(
        "billing",
        "Payment",
    )
    supplier_invoice_model = apps.get_model(
        "purchasing",
        "SupplierInvoice",
    )
    supplier_payment_model = apps.get_model(
        "purchasing",
        "SupplierPayment",
    )
    job_card_model = apps.get_model(
        "jobs",
        "JobCard",
    )

    customer_invoice = invoice_model.objects.get(
        **{
            ("work_order__job_card__vehicle__registration_number"): "UAT 505E",
        }
    )
    supplier_invoice = supplier_invoice_model.objects.get(
        supplier_reference="DEMO-SINV-UNPAID",
    )
    paid_release_job = job_card_model.objects.get(
        vehicle__registration_number="UAT 404D",
    )

    require(
        customer_invoice.status == "ISSUED",
        (f"UAT 505E invoice did not begin ISSUED: {customer_invoice.status}"),
    )
    require(
        supplier_invoice.status == "POSTED",
        (f"DEMO-SINV-UNPAID did not begin POSTED: {supplier_invoice.status}"),
    )
    require(
        paid_release_job.status != "RELEASED",
        "UAT 404D was already released.",
    )

    initial_customer_total = posted_payment_total(
        payment_model,
        relationship_filter={
            "invoice_id": customer_invoice.pk,
        },
    )
    initial_supplier_total = posted_payment_total(
        supplier_payment_model,
        relationship_filter={
            "supplier_invoice_id": supplier_invoice.pk,
        },
    )

    return Scenario(
        customer_invoice_id=customer_invoice.pk,
        supplier_invoice_id=supplier_invoice.pk,
        paid_release_job_id=paid_release_job.pk,
        initial_customer_payment_total=(initial_customer_total),
        initial_supplier_payment_total=(initial_supplier_total),
    )


def test_finance_reports(
    page: Page,
    context: BrowserContext,
) -> None:
    """Test permitted Cashier reports and CSV exports."""
    login(
        page,
        username="cashier",
        password="CashierDemo123!",
    )

    for report_name, paths in REPORTS.items():
        report_path, export_path = paths

        response = page.goto(
            full_url(report_path),
            wait_until="networkidle",
        )

        require_response(
            response,
            description=f"Cashier {report_name} report",
        )

        capture(
            page,
            f"UAT-CAS-01-{report_name}.png",
        )

        download_csv(
            context,
            path=export_path,
            destination=(CSV_DIR / f"UAT-CAS-01-{report_name}.csv"),
        )

    RESULTS["UAT-CAS-01"] = CaseResult(
        status="PASS",
        evidence=("`evidence/cashier/` and `evidence/csv/`"),
        notes=("Customer-finance and purchasing reports and CSV exports passed."),
    )


def test_customer_payment(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Record a partial customer payment."""
    response = page.goto(
        full_url(f"/billing/{scenario.customer_invoice_id}/payments/new/"),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Cashier customer-payment page",
    )

    amount_field = page.locator('[name="amount"]')
    method_field = page.locator('[name="payment_method"]')
    reference_field = page.locator('[name="external_reference"]')
    notes_field = page.locator('[name="notes"]')

    require(
        amount_field.count() == 1,
        "Customer-payment amount field was not shown.",
    )
    require(
        method_field.count() == 1,
        "Customer-payment method field was not shown.",
    )
    require(
        reference_field.count() == 1,
        "Customer-payment reference field was not shown.",
    )
    require(
        notes_field.count() == 1,
        "Customer-payment notes field was not shown.",
    )

    amount_field.fill("10000.00")
    method_field.select_option(label="Cash")
    reference_field.fill(CUSTOMER_PAYMENT_REFERENCE)
    notes_field.fill(CUSTOMER_PAYMENT_NOTES)

    submit_form(
        page,
        field_name="amount",
    )

    capture(
        page,
        "UAT-CAS-02-customer-payment.png",
    )


def test_supplier_payment(
    page: Page,
    *,
    scenario: Scenario,
) -> None:
    """Record a partial supplier payment."""
    response = page.goto(
        full_url(
            "/purchasing/supplier-invoices/"
            f"{scenario.supplier_invoice_id}/"
            "payments/new/"
        ),
        wait_until="networkidle",
    )

    require_response(
        response,
        description="Cashier supplier-payment page",
    )

    amount_field = page.locator('[name="amount"]')
    method_field = page.locator('[name="method"]')
    reference_field = page.locator('[name="external_reference"]')
    notes_field = page.locator('[name="notes"]')

    require(
        amount_field.count() == 1,
        "Supplier-payment amount field was not shown.",
    )
    require(
        method_field.count() == 1,
        "Supplier-payment method field was not shown.",
    )
    require(
        reference_field.count() == 1,
        "Supplier-payment reference field was not shown.",
    )
    require(
        notes_field.count() == 1,
        "Supplier-payment notes field was not shown.",
    )

    amount_field.fill("25000.00")
    method_field.select_option(
        label="Bank transfer",
    )
    reference_field.fill(SUPPLIER_PAYMENT_REFERENCE)
    notes_field.fill(SUPPLIER_PAYMENT_NOTES)

    submit_form(
        page,
        field_name="amount",
    )

    capture(
        page,
        "UAT-CAS-03-supplier-payment.png",
    )


def test_forbidden(
    page: Page,
    *,
    path: str,
    case_id: str,
    filename: str,
    description: str,
) -> None:
    """Verify one forbidden Cashier operation."""
    response = page.goto(
        full_url(path),
        wait_until="networkidle",
    )

    require(
        response is not None,
        f"{description} returned no HTTP response.",
    )
    require(
        response.status == 403,
        (f"{description} returned HTTP {response.status}; expected 403."),
    )

    capture(
        page,
        filename,
    )

    RESULTS[case_id] = CaseResult(
        status="PASS",
        evidence=(f"`evidence/cashier/{filename}`"),
        notes=(f"{description} correctly returned HTTP 403."),
    )


def verify_results(
    *,
    scenario: Scenario,
) -> None:
    """Verify both payments after Playwright stops."""
    invoice_model = apps.get_model(
        "billing",
        "Invoice",
    )
    payment_model = apps.get_model(
        "billing",
        "Payment",
    )
    supplier_invoice_model = apps.get_model(
        "purchasing",
        "SupplierInvoice",
    )
    supplier_payment_model = apps.get_model(
        "purchasing",
        "SupplierPayment",
    )

    customer_payment = payment_model.objects.get(
        external_reference=(CUSTOMER_PAYMENT_REFERENCE),
    )
    customer_invoice = invoice_model.objects.get(
        pk=scenario.customer_invoice_id,
    )

    require(
        customer_payment.invoice_id == scenario.customer_invoice_id,
        "Customer payment belongs to the wrong invoice.",
    )
    require(
        customer_payment.amount == CUSTOMER_PAYMENT_AMOUNT,
        "Customer payment amount is not 10000.00.",
    )
    require(
        customer_payment.payment_method == "CASH",
        "Customer payment method is not CASH.",
    )
    require(
        customer_payment.status == "POSTED",
        "Customer payment status is not POSTED.",
    )
    require(
        customer_payment.received_by.username == "cashier",
        "Customer payment was not recorded by cashier.",
    )
    require(
        customer_payment.notes == CUSTOMER_PAYMENT_NOTES,
        "Customer payment notes were not stored.",
    )

    customer_total = posted_payment_total(
        payment_model,
        relationship_filter={
            "invoice_id": scenario.customer_invoice_id,
        },
    )

    require(
        customer_total
        == (scenario.initial_customer_payment_total + CUSTOMER_PAYMENT_AMOUNT),
        "Customer posted-payment total is incorrect.",
    )
    require(
        customer_invoice.status == "PARTIALLY_PAID",
        (
            "Customer invoice status is "
            f"{customer_invoice.status}; "
            "expected PARTIALLY_PAID."
        ),
    )
    require(
        customer_invoice.total - customer_total > Decimal("0.00"),
        "Customer invoice no longer has a partial balance.",
    )

    supplier_payment = supplier_payment_model.objects.get(
        external_reference=(SUPPLIER_PAYMENT_REFERENCE),
    )
    supplier_invoice = supplier_invoice_model.objects.get(
        pk=scenario.supplier_invoice_id,
    )

    require(
        supplier_payment.supplier_invoice_id == scenario.supplier_invoice_id,
        "Supplier payment belongs to the wrong invoice.",
    )
    require(
        supplier_payment.amount == SUPPLIER_PAYMENT_AMOUNT,
        "Supplier payment amount is not 25000.00.",
    )
    require(
        supplier_payment.method == "BANK_TRANSFER",
        "Supplier payment method is not BANK_TRANSFER.",
    )
    require(
        supplier_payment.status == "POSTED",
        "Supplier payment status is not POSTED.",
    )
    require(
        supplier_payment.recorded_by.username == "cashier",
        "Supplier payment was not recorded by cashier.",
    )
    require(
        supplier_payment.notes == SUPPLIER_PAYMENT_NOTES,
        "Supplier payment notes were not stored.",
    )

    supplier_total = posted_payment_total(
        supplier_payment_model,
        relationship_filter={
            "supplier_invoice_id": (scenario.supplier_invoice_id),
        },
    )

    require(
        supplier_total
        == (scenario.initial_supplier_payment_total + SUPPLIER_PAYMENT_AMOUNT),
        "Supplier posted-payment total is incorrect.",
    )
    require(
        supplier_invoice.status == "PARTIALLY_PAID",
        (
            "Supplier invoice status is "
            f"{supplier_invoice.status}; "
            "expected PARTIALLY_PAID."
        ),
    )
    require(
        supplier_invoice.total - supplier_total > Decimal("0.00"),
        "Supplier invoice no longer has a partial balance.",
    )

    RESULTS["UAT-CAS-02"] = CaseResult(
        status="PASS",
        evidence=("`evidence/cashier/UAT-CAS-02-customer-payment.png`"),
        notes=("A UGX 10000.00 customer payment was recorded by cashier."),
    )
    RESULTS["UAT-CAS-03"] = CaseResult(
        status="PASS",
        evidence=("`evidence/cashier/UAT-CAS-03-supplier-payment.png`"),
        notes=("A UGX 25000.00 supplier payment was recorded by cashier."),
    )


def mark_failure(
    *,
    case_id: str,
    error: Exception,
    page: Page | None,
) -> None:
    """Record one Cashier automation failure."""
    evidence = ""

    if page is not None:
        try:
            if not page.is_closed():
                failure = capture(
                    page,
                    f"{case_id}-failure.png",
                )
                evidence = f"`evidence/cashier/{failure.name}`"
        except Exception:
            evidence = ""

    RESULTS[case_id] = CaseResult(
        status="FAIL",
        evidence=evidence,
        issue="AUTOMATED-UAT",
        notes=str(error).replace("|", "/"),
    )


def run() -> int:
    """Execute all Cashier UAT cases."""
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
    current_case = "UAT-CAS-01"

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

            current_case = "UAT-CAS-01"
            test_finance_reports(
                page,
                context,
            )

            current_case = "UAT-CAS-02"
            test_customer_payment(
                page,
                scenario=scenario,
            )

            current_case = "UAT-CAS-03"
            test_supplier_payment(
                page,
                scenario=scenario,
            )

            current_case = "UAT-CAS-04"
            test_forbidden(
                page,
                path="/reports/workshop-operations/",
                case_id=current_case,
                filename=("UAT-CAS-04-workshop-report-denied.png"),
                description=("Cashier workshop-report access"),
            )

            current_case = "UAT-CAS-05"
            test_forbidden(
                page,
                path="/reports/inventory-activity/",
                case_id=current_case,
                filename=("UAT-CAS-05-inventory-report-denied.png"),
                description=("Cashier inventory-report access"),
            )

            current_case = "UAT-CAS-06"
            test_forbidden(
                page,
                path=(f"/jobs/{scenario.paid_release_job_id}/release/"),
                case_id=current_case,
                filename=("UAT-CAS-06-vehicle-release-denied.png"),
                description=("Cashier vehicle-release access"),
            )

            context.close()
            browser.close()

        current_case = "UAT-CAS-02"
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
            f"Cashier UAT failed in {current_case}: {error}",
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

    print("Cashier browser UAT passed.")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"CSV directory: {CSV_DIR}")
    print(f"Execution ledger: {LEDGER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
