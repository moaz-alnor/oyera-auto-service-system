"""Regression tests for release security configuration."""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
CODEQL_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "codeql.yml"
CONTAINER_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "container.yml"
DEPENDABOT_CONFIG = ROOT_DIR / ".github" / "dependabot.yml"
DEVELOPMENT_REQUIREMENTS = ROOT_DIR / "requirements" / "development.txt"


def test_ci_uses_supported_action_versions() -> None:
    """CI should use reviewed GitHub Action major versions."""
    ci = CI_WORKFLOW.read_text(encoding="utf-8")
    codeql = CODEQL_WORKFLOW.read_text(encoding="utf-8")
    container = CONTAINER_WORKFLOW.read_text(encoding="utf-8")

    for workflow in (ci, codeql, container):
        assert "actions/checkout@v7" in workflow
        assert "actions/checkout@v8" not in workflow
        assert "persist-credentials: false" in workflow

    assert "actions/setup-python@v7" in ci
    assert "actions/setup-python@v8" not in ci


def test_ci_runs_dependency_and_python_security_gates() -> None:
    """CI should block vulnerable dependencies and unsafe code."""
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "pip-audit" in workflow
    assert "requirements/production.txt" in workflow
    assert "--requirement requirements/production.txt" in workflow

    assert "bandit" in workflow
    assert "--recursive src" in workflow
    assert "--severity-level medium" in workflow
    assert "--confidence-level medium" in workflow

    assert "pip-audit             --requirement" not in workflow
    assert "bandit             --recursive" not in workflow


def test_security_tools_are_reproducible_dependencies() -> None:
    """Security tools should remain below their next major versions."""
    requirements = DEVELOPMENT_REQUIREMENTS.read_text(encoding="utf-8").splitlines()

    assert any(
        line.startswith("pip-audit>=") and ",<3" in line for line in requirements
    )
    assert any(line.startswith("bandit>=") and ",<2" in line for line in requirements)


def test_dependabot_monitors_python_and_actions() -> None:
    """Dependabot should monitor dependencies without Django major bumps."""
    configuration = DEPENDABOT_CONFIG.read_text(encoding="utf-8")

    assert "package-ecosystem: pip" in configuration
    assert "package-ecosystem: github-actions" in configuration
    assert "package-ecosystem: docker" in configuration
    assert "target-branch: main" in configuration
    assert "dependency-name: django" in configuration
    assert "version-update:semver-major" in configuration


def test_codeql_scans_python_with_reviewed_major_action() -> None:
    """CodeQL should scan Python using a reviewed v4 release."""
    workflow = CODEQL_WORKFLOW.read_text(encoding="utf-8")

    assert re.search(
        r"github/codeql-action/init@v4(?:\.\d+\.\d+)?\b",
        workflow,
    )
    assert re.search(
        r"github/codeql-action/analyze@v4(?:\.\d+\.\d+)?\b",
        workflow,
    )
    assert "github/codeql-action/init@v5" not in workflow
    assert "github/codeql-action/analyze@v5" not in workflow
    assert "languages: python" in workflow
    assert "queries: security-extended" in workflow
    assert "security-events: write" in workflow
