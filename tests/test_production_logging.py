"""Regression tests for production logging configuration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

BASE_PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": (
        "production-logging-test-secret-key-2026-oyera-auto-service-system"
    ),
    "DJANGO_ALLOWED_HOSTS": "oyera.example.com",
    "POSTGRES_DB": "oyera_production_logging_test",
    "POSTGRES_USER": "oyera_production_logging_test",
    "POSTGRES_PASSWORD": "ProductionLoggingTestPassword2026!",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
}

LOGGING_SCRIPT = """
import json

import django

django.setup()

from django.conf import settings

print(json.dumps(settings.LOGGING))
"""


def _production_environment(**overrides: str) -> dict[str, str]:
    """Build an isolated production environment."""
    environment = os.environ.copy()
    environment.update(BASE_PRODUCTION_ENV)
    environment.update(overrides)

    python_path_entries = [str(SRC_DIR)]
    existing_python_path = environment.get("PYTHONPATH")

    if existing_python_path:
        python_path_entries.append(existing_python_path)

    environment["PYTHONPATH"] = os.pathsep.join(python_path_entries)
    return environment


def _read_logging_configuration(
    **overrides: str,
) -> dict[str, Any]:
    """Read production logging configuration in isolation."""
    completed = subprocess.run(
        [sys.executable, "-c", LOGGING_SCRIPT],
        cwd=ROOT_DIR,
        env=_production_environment(**overrides),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    return json.loads(completed.stdout)


def test_production_logging_uses_console_safe_defaults() -> None:
    """Production should emit consistent INFO logs to the console."""
    logging_config = _read_logging_configuration()

    assert logging_config["version"] == 1
    assert logging_config["disable_existing_loggers"] is False
    assert logging_config["handlers"]["console"]["class"] == ("logging.StreamHandler")
    assert logging_config["handlers"]["console"]["level"] == "INFO"
    assert logging_config["root"]["level"] == "INFO"
    assert logging_config["loggers"]["django"]["level"] == "INFO"
    assert logging_config["loggers"]["django.request"]["level"] == ("WARNING")
    assert logging_config["loggers"]["django.security"]["level"] == ("WARNING")
    assert logging_config["loggers"]["apps"]["level"] == "INFO"


def test_production_logging_reads_environment_level() -> None:
    """Operators should be able to raise the production log threshold."""
    logging_config = _read_logging_configuration(
        DJANGO_LOG_LEVEL=" warning ",
    )

    assert logging_config["handlers"]["console"]["level"] == ("WARNING")
    assert logging_config["root"]["level"] == "WARNING"
    assert logging_config["loggers"]["django"]["level"] == ("WARNING")
    assert logging_config["loggers"]["apps"]["level"] == ("WARNING")
