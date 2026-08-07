"""Regression tests for the role-by-role UAT casebook."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CASEBOOK = ROOT_DIR / "docs" / "uat" / "role-uat-casebook.md"
GENERATOR = ROOT_DIR / "scripts" / "generate_uat_casebook.py"


def test_casebook_contains_all_six_roles_and_accounts() -> None:
    """Every supported role should have exact credentials and cases."""
    content = CASEBOOK.read_text(encoding="utf-8")

    required_values = (
        "# Administrator UAT",
        "# Manager UAT",
        "# Receptionist UAT",
        "# Senior Technician UAT",
        "# Technician UAT",
        "# Cashier UAT",
        "`admin` | `AdminDemo123!`",
        "`manager` | `ManagerDemo123!`",
        "`receptionist` | `ReceptionDemo123!`",
        "`senior_technician` | `SeniorTechDemo123!`",
        "`technician` | `TechnicianDemo123!`",
        "`cashier` | `CashierDemo123!`",
    )

    for value in required_values:
        assert value in content


def test_casebook_uses_exact_seeded_business_scenarios() -> None:
    """Manual procedures should reference the real demo records."""
    content = CASEBOOK.read_text(encoding="utf-8")

    required_scenarios = (
        "DEMO-PO-SUBMITTED",
        "DEMO-SINV-UNPAID",
        "UAT 101A",
        "UAT 202B",
        "UAT 303C",
        "UAT 404D",
        "UAT 505E",
        "OIL-FILTER-001",
    )

    for scenario in required_scenarios:
        assert scenario in content


def test_casebook_tests_allowed_and_forbidden_access() -> None:
    """UAT must verify both successful work and permission denial."""
    content = CASEBOOK.read_text(encoding="utf-8")

    assert "Access Denied page or HTTP `403`" in content
    assert "CSV files" in content
    assert "Vehicle release is forbidden" in content
    assert "Task approval is forbidden" in content
    assert "Stock reservation is forbidden" in content


def test_casebook_defines_reset_evidence_and_acceptance_controls() -> None:
    """The tester should never need to guess how to run or record UAT."""
    content = CASEBOOK.read_text(encoding="utf-8")
    generator = GENERATOR.read_text(encoding="utf-8")

    assert "reset_demo_data --yes" in content
    assert "UAT-<ROLE>-<CASE>-<short-description>.png" in content
    assert "Result: __________" in content
    assert "Acceptance signatures" in content
    assert "reverse(" in generator
