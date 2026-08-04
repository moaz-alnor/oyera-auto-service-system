"""Regression tests for release security configuration."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
CODEQL_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "codeql.yml"
DEPENDABOT_CONFIG = ROOT_DIR / ".github" / "dependabot.yml"
DEVELOPMENT_REQUIREMENTS = ROOT_DIR / "requirements" / "development.txt"


def test_ci_uses_supported_action_versions() -> None:
    """CI should use released GitHub Action major versions."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/checkout@v7" not in workflow
    assert "actions/setup-python@v7" not in workflow
    assert "persist-credentials: false" in workflow


def test_ci_runs_dependency_and_python_security_gates() -> None:
    """CI should block vulnerable dependencies and unsafe code."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "pip-audit" in workflow
    assert "requirements/production.txt" in workflow
    assert "bandit" in workflow
    assert "--severity-level medium" in workflow
    assert "--confidence-level medium" in workflow
    assert (
        "pip-audit \\\n            --requirement requirements/production.txt"
    ) in workflow
    assert ("bandit \\\n            --recursive src") in workflow
    assert "pip-audit             --requirement" not in workflow
    assert "bandit             --recursive" not in workflow


def test_security_tools_are_reproducible_dependencies() -> None:
    """Security tools should be installed from project requirements."""
    requirements = DEVELOPMENT_REQUIREMENTS.read_text(encoding="utf-8")

    assert "pip-audit>=2.10,<3" in requirements
    assert "bandit>=1.9,<2" in requirements


def test_dependabot_monitors_python_and_actions() -> None:
    """Dependabot should monitor both dependency ecosystems."""
    configuration = DEPENDABOT_CONFIG.read_text(encoding="utf-8")

    assert "package-ecosystem: pip" in configuration
    assert "package-ecosystem: github-actions" in configuration
    assert "target-branch: main" in configuration


def test_codeql_scans_python_with_current_action() -> None:
    """CodeQL should scan Python using the current major action."""
    workflow = CODEQL_WORKFLOW.read_text(encoding="utf-8")

    assert "github/codeql-action/init@v4" in workflow
    assert "github/codeql-action/analyze@v4" in workflow
    assert "languages: python" in workflow
    assert "queries: security-extended" in workflow
    assert "security-events: write" in workflow
