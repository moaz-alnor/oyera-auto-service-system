"""Execute Receptionist browser UAT and capture real evidence."""

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

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

django.setup()

ROOT_DIR: Final = Path(__file__).resolve().parents[1]

EVIDENCE_DIR: Final = ROOT_DIR / "docs" / "uat" / "evidence" / "receptionist"
LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"
SERVER_LOG: Final = Path("/tmp/oyera-receptionist-uat-server.log")

RESULTS: dict[str, CaseResult] = {
    "UAT-REC-01": CaseResult(),
    "UAT-REC-02": CaseResult(),
    "UAT-REC-03": CaseResult(),
    "UAT-REC-04": CaseResult(),
    "UAT-REC-05": CaseResult(),
    "UAT-REC-06": CaseResult(),
}


def start_server() -> subprocess.Popen[str]:
    """Start a dedicated Receptionist UAT server."""
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
    """Capture one full-page Receptionist screenshot."""
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
    """Remove evidence from an incomplete earlier run."""
    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in EVIDENCE_DIR.glob("UAT-REC-*"):
        path.unlink(missing_ok=True)


def reset_ledger_rows() -> None:
    """Reset Receptionist ledger rows to NOT RUN."""
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
    """Write Receptionist results into the ledger."""
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


def select_option_containing(
    page: Page,
    *,
    field_name: str,
    expected_text: str,
) -> None:
    """Select the option containing the supplied text."""
    select = page.locator(f'[name="{field_name}"]')
    require(
        select.count() == 1,
        f"Select field {field_name!r} was not found.",
    )

    options = select.locator("option")
    option_count = options.count()

    for index in range(option_count):
        option = options.nth(index)
        label = option.inner_text().strip()

        if expected_text.casefold() in label.casefold():
            value = option.get_attribute("value")
            require(
                value is not None,
                (f"Option {expected_text!r} has no selectable value."),
            )
            select.select_option(value=value)
            return

    available = [
        options.nth(index).inner_text().strip() for index in range(option_count)
    ]

    raise AssertionError(
        f"Could not find {expected_text!r} in {field_name!r}. Options: {available}"
    )


def prepare_scenario_ids() -> tuple[int, int]:
    """Resolve paid-release and forbidden-stock scenarios."""
    job_card_model = apps.get_model(
        "jobs",
        "JobCard",
    )
    requirement_model = apps.get_model(
        "workshop",
        "WorkProductRequirement",
    )

    paid_job = job_card_model.objects.get(
        vehicle__registration_number="UAT 404D",
    )
    requirement = requirement_model.objects.get(
        work_order__job_card__vehicle__registration_number=("UAT 101A"),
    )

    require(
        paid_job.status != "RELEASED",
        "UAT 404D was already released.",
    )

    return (
        paid_job.pk,
        requirement.pk,
    )


def test_create_customer(page: Page) -> None:
    """Register the Receptionist UAT customer."""
    login(
        page,
        username="receptionist",
        password="ReceptionDemo123!",
    )

    response = page.goto(
        full_url("/customers/new/"),
        wait_until="networkidle",
    )
    require_response(
        response,
        description="Customer registration page",
    )

    page.locator('[name="customer_type"]').select_option(label="Individual")
    page.locator('[name="name"]').fill("UAT Reception Customer")
    page.locator('[name="phone_number"]').fill("+256700900101")
    page.locator('[name="email"]').fill("uat.reception@example.com")
    page.locator('[name="address"]').fill("Kampala UAT Address")
    page.locator('[name="notes"]').fill("Created during Receptionist UAT.")

    submit_form(
        page,
        field_name="name",
    )

    require(
        "UAT Reception Customer" in page.locator("body").inner_text(),
        "Created customer was not displayed.",
    )

    capture(
        page,
        "UAT-REC-01-customer-created.png",
    )


def test_create_vehicle(page: Page) -> None:
    """Register a vehicle for the new UAT customer."""
    response = page.goto(
        full_url("/vehicles/new/"),
        wait_until="networkidle",
    )
    require_response(
        response,
        description="Vehicle registration page",
    )

    select_option_containing(
        page,
        field_name="current_owner",
        expected_text="UAT Reception Customer",
    )

    page.locator('[name="registration_number"]').fill("UAT 606F")

    page.locator('[name="category"]').select_option(label="Small vehicle")

    page.locator('[name="make"]').fill("Toyota")
    page.locator('[name="model"]').fill("Yaris")
    page.locator('[name="year"]').fill("2021")
    page.locator('[name="color"]').fill("Blue")
    page.locator('[name="current_mileage"]').fill("60600")

    page.locator('[name="fuel_type"]').select_option(label="Petrol")

    page.locator('[name="notes"]').fill("Created during Receptionist UAT.")

    submit_form(
        page,
        field_name="registration_number",
    )

    require(
        "UAT 606F" in page.locator("body").inner_text(),
        "Created vehicle was not displayed.",
    )

    capture(
        page,
        "UAT-REC-02-vehicle-created.png",
    )


def test_create_job(page: Page) -> None:
    """Open a job card for the new vehicle."""
    response = page.goto(
        full_url("/jobs/new/"),
        wait_until="networkidle",
    )
    require_response(
        response,
        description="Job-card creation page",
    )

    select_option_containing(
        page,
        field_name="customer",
        expected_text="UAT Reception Customer",
    )
    select_option_containing(
        page,
        field_name="vehicle",
        expected_text="UAT 606F",
    )

    page.locator('[name="arrival_mileage"]').fill("60600")
    page.locator('[name="customer_complaint"]').fill(
        "Customer reports engine oil warning during UAT."
    )
    page.locator('[name="visible_condition"]').fill(
        "No external damage observed during intake."
    )
    page.locator('[name="fuel_level"]').select_option(label="Half")
    page.locator('[name="priority"]').select_option(label="Normal")

    submit_form(
        page,
        field_name="arrival_mileage",
    )

    body = page.locator("body").inner_text()

    require(
        "UAT 606F" in body,
        "New job card does not show UAT 606F.",
    )
    require(
        "engine oil warning" in body.lower(),
        "Customer complaint was not displayed.",
    )

    capture(
        page,
        "UAT-REC-03-job-card-created.png",
    )


def test_paid_release(
    page: Page,
    *,
    job_card_id: int,
) -> None:
    """Release the fully paid UAT 404D vehicle."""
    response = page.goto(
        full_url(f"/jobs/{job_card_id}/release/"),
        wait_until="networkidle",
    )
    require_response(
        response,
        description="Paid vehicle-release page",
    )

    body = page.locator("body").inner_text()
    require(
        "UAT 404D" in body,
        "Paid UAT 404D scenario was not displayed.",
    )

    page.locator('[name="final_mileage"]').fill("40400")
    page.locator('[name="final_condition"]').fill(
        "Vehicle clean and ready for customer collection."
    )
    page.locator('[name="received_by_name"]').fill("UAT Paid Customer")
    page.locator('[name="received_by_contact"]').fill("+256700000404")
    page.locator('[name="handover_notes"]').fill(
        "Keys and service documents handed over."
    )

    require(
        page.locator('[name="payment_override"]').count() == 0,
        ("Receptionist unexpectedly received a payment-override control."),
    )

    submit_form(
        page,
        field_name="final_mileage",
    )

    capture(
        page,
        "UAT-REC-04-paid-release.png",
    )


def test_forbidden(
    page: Page,
    *,
    path: str,
    case_id: str,
    filename: str,
    description: str,
) -> None:
    """Verify one Receptionist permission denial."""
    response = page.goto(
        full_url(path),
        wait_until="networkidle",
    )

    require(
        response is not None,
        f"{description} returned no response.",
    )
    require(
        response.status == 403,
        (f"{description} returned HTTP {response.status}; expected 403."),
    )

    body = page.locator("body").inner_text()

    require(
        (
            "access denied" in body.lower()
            or "permission" in body.lower()
            or "forbidden" in body.lower()
        ),
        (f"{description} did not display an access-denied message."),
    )

    capture(
        page,
        filename,
    )

    RESULTS[case_id] = CaseResult(
        status="PASS",
        evidence=(f"`evidence/receptionist/{filename}`"),
        notes=f"{description} correctly returned HTTP 403.",
    )


def verify_created_records(
    *,
    paid_job_card_id: int,
) -> None:
    """Verify all successful Receptionist changes."""
    customer_model = apps.get_model(
        "customers",
        "Customer",
    )
    vehicle_model = apps.get_model(
        "vehicles",
        "Vehicle",
    )
    job_card_model = apps.get_model(
        "jobs",
        "JobCard",
    )
    release_model = apps.get_model(
        "jobs",
        "VehicleRelease",
    )

    customer = customer_model.objects.get(
        name="UAT Reception Customer",
    )
    vehicle = vehicle_model.objects.get(
        registration_number="UAT 606F",
    )
    new_job = job_card_model.objects.get(
        vehicle=vehicle,
    )
    paid_job = job_card_model.objects.get(
        pk=paid_job_card_id,
    )
    release = release_model.objects.get(
        job_card_id=paid_job_card_id,
    )

    require(
        bool(customer.customer_number),
        "Created customer has no customer number.",
    )
    require(
        customer.phone_number == "+256700900101",
        "Customer phone number was not stored correctly.",
    )
    require(
        customer.email == "uat.reception@example.com",
        "Customer email was not stored correctly.",
    )

    require(
        vehicle.current_owner_id == customer.pk,
        "Vehicle is not linked to the new customer.",
    )
    require(
        vehicle.current_mileage == 60600,
        "Vehicle mileage was not stored correctly.",
    )

    require(
        new_job.customer_id == customer.pk,
        "Job card is not linked to the new customer.",
    )
    require(
        new_job.arrival_mileage == 60600,
        "Job-card arrival mileage is incorrect.",
    )
    require(
        new_job.status == "OPEN",
        (f"New job status is {new_job.status}; expected OPEN."),
    )

    require(
        paid_job.status == "RELEASED",
        (f"UAT 404D status is {paid_job.status}; expected RELEASED."),
    )
    require(
        release.payment_override is False,
        "Paid release incorrectly contains an override.",
    )
    require(
        release.outstanding_amount_snapshot == Decimal("0.00"),
        "Paid release does not have a zero balance.",
    )
    require(
        release.released_by.username == "receptionist",
        "Vehicle was not released by receptionist.",
    )
    require(
        release.received_by_name == "UAT Paid Customer",
        "Release receiver was not stored correctly.",
    )

    RESULTS["UAT-REC-01"] = CaseResult(
        status="PASS",
        evidence=("`evidence/receptionist/UAT-REC-01-customer-created.png`"),
        notes=("Customer was created with a generated customer number."),
    )
    RESULTS["UAT-REC-02"] = CaseResult(
        status="PASS",
        evidence=("`evidence/receptionist/UAT-REC-02-vehicle-created.png`"),
        notes=("UAT 606F was registered to the new customer."),
    )
    RESULTS["UAT-REC-03"] = CaseResult(
        status="PASS",
        evidence=("`evidence/receptionist/UAT-REC-03-job-card-created.png`"),
        notes=("An OPEN job card was created for UAT 606F."),
    )
    RESULTS["UAT-REC-04"] = CaseResult(
        status="PASS",
        evidence=("`evidence/receptionist/UAT-REC-04-paid-release.png`"),
        notes=("Fully paid UAT 404D was released without a payment override."),
    )


def mark_failure(
    *,
    case_id: str,
    error: Exception,
    page: Page | None,
) -> None:
    """Record one Receptionist automation failure."""
    evidence = ""

    if page is not None:
        try:
            if not page.is_closed():
                failure = capture(
                    page,
                    f"{case_id}-failure.png",
                )
                evidence = f"`evidence/receptionist/{failure.name}`"
        except Exception:
            evidence = ""

    RESULTS[case_id] = CaseResult(
        status="FAIL",
        evidence=evidence,
        issue="AUTOMATED-UAT",
        notes=str(error).replace("|", "/"),
    )


def run() -> int:
    """Execute all Receptionist UAT cases."""
    clear_evidence()
    reset_ledger_rows()

    call_command(
        "reset_demo_data",
        yes=True,
        verbosity=0,
    )

    paid_job_id, requirement_id = prepare_scenario_ids()

    server = start_server()
    page: Page | None = None
    current_case = "UAT-REC-01"

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

            current_case = "UAT-REC-01"
            test_create_customer(page)

            current_case = "UAT-REC-02"
            test_create_vehicle(page)

            current_case = "UAT-REC-03"
            test_create_job(page)

            current_case = "UAT-REC-04"
            test_paid_release(
                page,
                job_card_id=paid_job_id,
            )

            current_case = "UAT-REC-05"
            test_forbidden(
                page,
                path="/billing/",
                case_id=current_case,
                filename="UAT-REC-05-billing-denied.png",
                description="Receptionist billing access",
            )

            current_case = "UAT-REC-06"
            test_forbidden(
                page,
                path=(f"/inventory/requirements/{requirement_id}/reserve/"),
                case_id=current_case,
                filename=("UAT-REC-06-stock-reservation-denied.png"),
                description=("Receptionist stock-reservation access"),
            )

            context.close()
            browser.close()

        current_case = "UAT-REC-01"
        verify_created_records(
            paid_job_card_id=paid_job_id,
        )

    except Exception as error:
        mark_failure(
            case_id=current_case,
            error=error,
            page=page,
        )
        write_results()

        print(
            f"Receptionist UAT failed in {current_case}: {error}",
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

    print("Receptionist browser UAT passed.")
    print(f"Evidence directory: {EVIDENCE_DIR}")
    print(f"Execution ledger: {LEDGER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
