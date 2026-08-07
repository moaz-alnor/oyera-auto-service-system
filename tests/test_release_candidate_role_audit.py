"""Tests for the release-candidate role audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT_DIR = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT_DIR / "scripts" / "release_candidate_role_audit.py"


def _load_audit_module() -> ModuleType:
    """Load the audit script without executing its main function."""
    specification = importlib.util.spec_from_file_location(
        "release_candidate_role_audit",
        AUDIT_SCRIPT,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError("Could not load the release-candidate audit.")

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_audit_uses_an_approved_local_host() -> None:
    """The audit should not rely on Django's testserver host."""
    audit = _load_audit_module()

    assert audit.AUDIT_HOST == "localhost"
    assert audit.AUDIT_HOST != "testserver"


def test_audit_classifies_http_responses() -> None:
    """Every relevant HTTP response should have a clear label."""
    audit = _load_audit_module()

    assert audit._classification(200) == "SUCCESS"
    assert audit._classification(302) == "REDIRECT"
    assert audit._classification(400) == "BAD REQUEST"
    assert audit._classification(403) == "FORBIDDEN"
    assert audit._classification(404) == "NOT FOUND"
    assert audit._classification(500) == "SERVER ERROR"


def test_audit_rejects_unexpected_error_responses() -> None:
    """Only successful, redirect, and forbidden responses are valid."""
    audit = _load_audit_module()

    assert audit._is_expected_scenario_status(200) is True
    assert audit._is_expected_scenario_status(204) is True
    assert audit._is_expected_scenario_status(302) is True
    assert audit._is_expected_scenario_status(403) is True

    assert audit._is_expected_scenario_status(400) is False
    assert audit._is_expected_scenario_status(404) is False
    assert audit._is_expected_scenario_status(500) is False
