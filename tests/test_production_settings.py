"""Regression tests for production-only security settings."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
MANAGE_PY = SRC_DIR / "manage.py"

BASE_PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": (
        "production-settings-test-secret-key-2026-oyera-auto-service-system"
    ),
    "DJANGO_ALLOWED_HOSTS": "oyera.example.com",
    "POSTGRES_DB": "oyera_production_settings_test",
    "POSTGRES_USER": "oyera_production_settings_test",
    "POSTGRES_PASSWORD": "ProductionSettingsTestPassword2026!",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
}

SETTINGS_SCRIPT = """
import json

import django

django.setup()

from django.conf import settings

print(
    json.dumps(
        {
            "debug": settings.DEBUG,
            "allowed_hosts": settings.ALLOWED_HOSTS,
            "session_cookie_secure": settings.SESSION_COOKIE_SECURE,
            "csrf_cookie_secure": settings.CSRF_COOKIE_SECURE,
            "ssl_redirect": settings.SECURE_SSL_REDIRECT,
            "secure_proxy_ssl_header": (
                settings.SECURE_PROXY_SSL_HEADER
            ),
            "hsts_seconds": settings.SECURE_HSTS_SECONDS,
            "hsts_include_subdomains": (
                settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
            ),
            "hsts_preload": settings.SECURE_HSTS_PRELOAD,
        }
    )
)
"""


def _production_environment(**overrides: str) -> dict[str, str]:
    """Build an isolated environment for production-settings checks."""
    environment = os.environ.copy()
    environment.update(BASE_PRODUCTION_ENV)
    environment.update(overrides)

    python_path_entries = [str(SRC_DIR)]
    existing_python_path = environment.get("PYTHONPATH")

    if existing_python_path:
        python_path_entries.append(existing_python_path)

    environment["PYTHONPATH"] = os.pathsep.join(python_path_entries)
    return environment


def _read_production_settings(**overrides: str) -> dict[str, Any]:
    """Load selected production settings in an isolated Python process."""
    completed = subprocess.run(
        [sys.executable, "-c", SETTINGS_SCRIPT],
        cwd=ROOT_DIR,
        env=_production_environment(**overrides),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    return json.loads(completed.stdout)


def test_production_settings_use_safe_hsts_defaults() -> None:
    """HSTS should remain disabled until deployment explicitly enables it."""
    settings = _read_production_settings()

    assert settings == {
        "debug": False,
        "allowed_hosts": ["oyera.example.com"],
        "session_cookie_secure": True,
        "csrf_cookie_secure": True,
        "ssl_redirect": True,
        "secure_proxy_ssl_header": None,
        "hsts_seconds": 0,
        "hsts_include_subdomains": False,
        "hsts_preload": False,
    }


def test_production_settings_read_hsts_environment_values() -> None:
    """Production should parse explicit HSTS deployment configuration."""
    settings = _read_production_settings(
        DJANGO_ALLOWED_HOSTS=(" oyera.example.com, admin.oyera.example.com "),
        DJANGO_TRUST_X_FORWARDED_PROTO=" TrUe ",
        DJANGO_SECURE_HSTS_SECONDS="31536000",
        DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=" TrUe ",
        DJANGO_SECURE_HSTS_PRELOAD="true",
    )

    assert settings["allowed_hosts"] == [
        "oyera.example.com",
        "admin.oyera.example.com",
    ]
    assert settings["secure_proxy_ssl_header"] == [
        "HTTP_X_FORWARDED_PROTO",
        "https",
    ]
    assert settings["hsts_seconds"] == 31536000
    assert settings["hsts_include_subdomains"] is True
    assert settings["hsts_preload"] is True


def test_production_deployment_check_has_no_warnings() -> None:
    """The target production configuration should pass deployment checks."""
    completed = subprocess.run(
        [
            sys.executable,
            str(MANAGE_PY),
            "check",
            "--deploy",
            "--fail-level",
            "WARNING",
        ],
        cwd=ROOT_DIR,
        env=_production_environment(
            DJANGO_SECURE_HSTS_SECONDS="31536000",
            DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS="true",
            DJANGO_SECURE_HSTS_PRELOAD="true",
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    combined_output = f"{completed.stdout}\n{completed.stderr}"

    assert completed.returncode == 0, combined_output
    assert "System check identified no issues" in combined_output
