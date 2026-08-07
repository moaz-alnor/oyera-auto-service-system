"""Run all OYERA role-based browser UAT suites."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT_DIR: Final = Path(__file__).resolve().parents[1]

ROLE_SCRIPTS: Final = (
    "run_administrator_uat.py",
    "run_manager_uat.py",
    "run_receptionist_uat.py",
    "run_senior_technician_uat.py",
    "run_technician_uat.py",
    "run_cashier_uat.py",
)

LEDGER_PATH: Final = ROOT_DIR / "docs" / "uat" / "uat-execution-results.md"

EXPECTED_SCREENSHOTS: Final = {
    "administrator": 7,
    "manager": 8,
    "receptionist": 6,
    "senior-technician": 8,
    "technician": 5,
    "cashier": 7,
}

EXPECTED_CSV_FILES: Final = 10
EXPECTED_CASES: Final = 32


def run_role_script(
    script_name: str,
) -> None:
    """Run one role UAT script and stop on failure."""
    script_path = ROOT_DIR / "scripts" / script_name

    print()
    print("=" * 72)
    print(f"Running {script_name}")
    print("=" * 72)

    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": ("config.settings.development"),
            "PYTHONPATH": str(ROOT_DIR / "src"),
        }
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=ROOT_DIR,
        env=environment,
        check=False,
    )

    if completed.returncode != 0:
        raise SystemExit(
            f"{script_name} failed with exit status {completed.returncode}."
        )


def validate_ledger() -> None:
    """Require all 32 UAT cases to be marked PASS."""
    if not LEDGER_PATH.exists():
        raise SystemExit(f"UAT ledger was not found: {LEDGER_PATH}")

    content = LEDGER_PATH.read_text(encoding="utf-8")

    cases = re.findall(
        r"^\| (UAT-[A-Z]+-\d+) \| "
        r"(PASS|FAIL|BLOCKED|NOT RUN) \|",
        content,
        flags=re.MULTILINE,
    )

    if len(cases) != EXPECTED_CASES:
        raise SystemExit(f"Expected {EXPECTED_CASES} UAT cases; found {len(cases)}.")

    non_passing = [(case_id, status) for case_id, status in cases if status != "PASS"]

    if non_passing:
        details = ", ".join(f"{case_id}={status}" for case_id, status in non_passing)
        raise SystemExit(f"Non-passing UAT cases remain: {details}")

    print(f"UAT ledger passed: {len(cases)}/{EXPECTED_CASES} cases.")


def validate_screenshots() -> None:
    """Require every expected role screenshot."""
    evidence_root = ROOT_DIR / "docs" / "uat" / "evidence"

    total = 0

    for role, expected_count in EXPECTED_SCREENSHOTS.items():
        role_directory = evidence_root / role

        screenshots = sorted(role_directory.glob("UAT-*.png"))

        if len(screenshots) != expected_count:
            raise SystemExit(
                f"{role}: expected {expected_count} "
                f"screenshots; found {len(screenshots)}."
            )

        for screenshot in screenshots:
            data = screenshot.read_bytes()

            if data[:8] != b"\x89PNG\r\n\x1a\n":
                raise SystemExit(f"Invalid PNG evidence: {screenshot}")

            if len(data) == 0:
                raise SystemExit(f"Empty screenshot: {screenshot}")

        total += len(screenshots)

        print(f"{role}: {len(screenshots)} screenshots passed.")

    print(f"Screenshot evidence passed: {total} files.")


def validate_csv_files() -> None:
    """Require all report CSV evidence files."""
    csv_directory = ROOT_DIR / "docs" / "uat" / "evidence" / "csv"

    csv_files = sorted(csv_directory.glob("UAT-*.csv"))

    if len(csv_files) != EXPECTED_CSV_FILES:
        raise SystemExit(
            f"Expected {EXPECTED_CSV_FILES} CSV files; found {len(csv_files)}."
        )

    for csv_file in csv_files:
        data = csv_file.read_bytes()

        if not data:
            raise SystemExit(f"Empty CSV evidence: {csv_file}")

        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise SystemExit(f"Invalid UTF-8 CSV: {csv_file}") from error

        populated_lines = [line for line in text.splitlines() if line.strip()]

        if not populated_lines:
            raise SystemExit(f"CSV contains no populated rows: {csv_file}")

    print(f"CSV evidence passed: {len(csv_files)} files.")


def main() -> int:
    """Execute and validate the entire OYERA UAT package."""
    for script_name in ROLE_SCRIPTS:
        run_role_script(script_name)

    print()
    print("=" * 72)
    print("Validating consolidated UAT evidence")
    print("=" * 72)

    validate_ledger()
    validate_screenshots()
    validate_csv_files()

    print()
    print("OYERA consolidated role-based UAT passed: 32/32 cases.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
