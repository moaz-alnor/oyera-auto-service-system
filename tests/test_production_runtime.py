"""Regression tests for the OYERA production runtime."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
MANAGE_PY = SRC_DIR / "manage.py"
GUNICORN_CONFIG = ROOT_DIR / "gunicorn.conf.py"

BASE_PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": (
        "production-runtime-test-secret-key-2026-oyera-auto-service-system"
    ),
    "DJANGO_ALLOWED_HOSTS": "oyera.example.com",
    "POSTGRES_DB": "oyera_production_runtime_test",
    "POSTGRES_USER": "oyera_production_runtime_test",
    "POSTGRES_PASSWORD": "ProductionRuntimeTestPassword2026!",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "DJANGO_SECURE_HSTS_SECONDS": "31536000",
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "true",
    "DJANGO_SECURE_HSTS_PRELOAD": "true",
}

SETTINGS_SCRIPT = """
import json

import django

django.setup()

from django.conf import settings

print(
    json.dumps(
        {
            "middleware": settings.MIDDLEWARE,
            "storages": settings.STORAGES,
            "static_root": str(settings.STATIC_ROOT),
            "media_root": str(settings.MEDIA_ROOT),
        }
    )
)
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


def _read_runtime_settings(**overrides: str) -> dict[str, Any]:
    """Read selected runtime settings in an isolated process."""
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


def test_production_uses_whitenoise_after_security_middleware(
    tmp_path: Path,
) -> None:
    """WhiteNoise should be ordered correctly and use manifest storage."""
    static_root = tmp_path / "staticfiles"
    media_root = tmp_path / "media"

    settings = _read_runtime_settings(
        DJANGO_STATIC_ROOT=str(static_root),
        DJANGO_MEDIA_ROOT=str(media_root),
    )

    middleware = settings["middleware"]

    assert middleware[0] == ("django.middleware.security.SecurityMiddleware")
    assert middleware[1] == ("whitenoise.middleware.WhiteNoiseMiddleware")
    assert settings["storages"]["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
    assert settings["storages"]["default"]["BACKEND"] == (
        "django.core.files.storage.FileSystemStorage"
    )
    assert settings["static_root"] == str(static_root)
    assert settings["media_root"] == str(media_root)


def test_collectstatic_creates_manifest_and_compressed_assets(
    tmp_path: Path,
) -> None:
    """Production collection should create hashed and compressed assets."""
    static_root = tmp_path / "staticfiles"
    media_root = tmp_path / "media"

    completed = subprocess.run(
        [
            sys.executable,
            str(MANAGE_PY),
            "collectstatic",
            "--noinput",
            "--clear",
            "--verbosity",
            "0",
        ],
        cwd=ROOT_DIR,
        env=_production_environment(
            DJANGO_STATIC_ROOT=str(static_root),
            DJANGO_MEDIA_ROOT=str(media_root),
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    combined_output = f"{completed.stdout}\n{completed.stderr}"
    assert completed.returncode == 0, combined_output

    manifest_path = static_root / "staticfiles.json"

    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = manifest["paths"]

    required_assets = {
        "css/tokens.css",
        "css/base.css",
        "css/layout.css",
        "css/components.css",
    }

    assert required_assets <= paths.keys()

    for asset in required_assets:
        assert paths[asset] != asset
        assert (static_root / paths[asset]).exists()

    assert list(static_root.rglob("*.gz"))


def test_gunicorn_configuration_is_valid() -> None:
    """Gunicorn should accept the committed production configuration."""
    completed = subprocess.run(
        [
            "gunicorn",
            "--check-config",
            "--config",
            str(GUNICORN_CONFIG),
            "config.wsgi:application",
        ],
        cwd=ROOT_DIR,
        env=_production_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    combined_output = f"{completed.stdout}\n{completed.stderr}"

    assert completed.returncode == 0, combined_output


def test_gunicorn_control_socket_is_disabled_by_default(
    monkeypatch,
) -> None:
    """The operational control socket should require explicit opt-in."""
    monkeypatch.delenv(
        "GUNICORN_ENABLE_CONTROL_SOCKET",
        raising=False,
    )
    monkeypatch.delenv(
        "GUNICORN_CONTROL_SOCKET",
        raising=False,
    )

    config = runpy.run_path(str(GUNICORN_CONFIG))

    assert config["control_socket_disable"] is True
    assert config["control_socket"] == "/tmp/oyera-gunicorn.ctl"
    assert config["control_socket_mode"] == 0o600


def test_gunicorn_control_socket_can_be_enabled(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Operators should be able to enable a protected control socket."""
    socket_path = tmp_path / "oyera.ctl"

    monkeypatch.setenv(
        "GUNICORN_ENABLE_CONTROL_SOCKET",
        " TrUe ",
    )
    monkeypatch.setenv(
        "GUNICORN_CONTROL_SOCKET",
        str(socket_path),
    )

    config = runpy.run_path(str(GUNICORN_CONFIG))

    assert config["control_socket_disable"] is False
    assert config["control_socket"] == str(socket_path)
    assert config["control_socket_mode"] == 0o600
