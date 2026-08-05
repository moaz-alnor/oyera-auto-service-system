"""Regression tests for the generated UAT baseline."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATOR = ROOT_DIR / "scripts" / "generate_uat_baseline.py"
BASELINE = ROOT_DIR / "docs" / "uat" / "uat-baseline.md"


def test_uat_generator_defines_all_six_demo_accounts() -> None:
    """The generator should cover every supported employee role."""
    content = GENERATOR.read_text(encoding="utf-8")

    expected_credentials = (
        '"admin",\n        "AdminDemo123!"',
        '"manager",\n        "ManagerDemo123!"',
        '"receptionist",\n        "ReceptionDemo123!"',
        '"senior_technician",\n        "SeniorTechDemo123!"',
        '"technician",\n        "TechnicianDemo123!"',
        '"cashier",\n        "CashierDemo123!"',
    )

    for credentials in expected_credentials:
        assert credentials in content


def test_uat_baseline_records_successful_role_access() -> None:
    """Every role should authenticate and open its dashboard."""
    content = BASELINE.read_text(encoding="utf-8")

    expected_rows = (
        "| Administrator | `admin` | `AdminDemo123!` | PASS | 200 |",
        "| Manager | `manager` | `ManagerDemo123!` | PASS | 200 |",
        ("| Receptionist | `receptionist` | `ReceptionDemo123!` | PASS | 200 |"),
        (
            "| Senior Technician | `senior_technician` | "
            "`SeniorTechDemo123!` | PASS | 200 |"
        ),
        ("| Technician | `technician` | `TechnicianDemo123!` | PASS | 200 |"),
        "| Cashier | `cashier` | `CashierDemo123!` | PASS | 200 |",
    )

    for row in expected_rows:
        assert row in content

    assert "| FAIL |" not in content
    assert (
        "**PASS — all six accounts authenticated and "
        "all dashboards returned HTTP 200.**" in content
    )


def test_uat_baseline_handles_permission_only_models() -> None:
    """Unmanaged permission models must not be queried as tables."""
    content = BASELINE.read_text(encoding="utf-8")

    assert (
        "| `reports.ReportAccess` | Not applicable | "
        "Unmanaged permission model |" in content
    )
    assert "reports_reportaccess" not in content
    assert "SQL error" not in content
