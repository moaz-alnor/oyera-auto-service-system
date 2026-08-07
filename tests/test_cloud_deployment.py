"""Regression tests for Render, Neon, and R2 deployment."""

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

PRODUCTION_SETTINGS_SCRIPT = """
import json

import django

django.setup()

from django.conf import settings

print(
    json.dumps(
        {
            "allowed_hosts": settings.ALLOWED_HOSTS,
            "database": settings.DATABASES["default"],
            "default_storage": settings.STORAGES["default"],
        }
    )
)
"""


def _cloud_environment(
    **overrides: str,
) -> dict[str, str]:
    """Build an isolated cloud production environment."""
    environment = os.environ.copy()

    for name in (
        "DJANGO_ALLOWED_HOSTS",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ):
        environment.pop(name, None)

    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": ("config.settings.production"),
            "DJANGO_SECRET_KEY": (
                "cloud-deployment-test-secret-key-2026-oyera-auto-service-system"
            ),
            "RENDER_EXTERNAL_HOSTNAME": ("oyera-auto-service-system.onrender.com"),
            "DATABASE_URL": (
                "postgresql://oyera_test:"
                "Password2026%21@"
                "ep-example.eu-central-1.aws.neon.tech/"
                "oyera_test"
                "?sslmode=require"
                "&channel_binding=require"
            ),
            "USE_R2_STORAGE": "false",
        }
    )
    environment.update(overrides)

    python_path = [str(SRC_DIR)]
    existing = environment.get("PYTHONPATH")

    if existing:
        python_path.append(existing)

    environment["PYTHONPATH"] = os.pathsep.join(python_path)

    return environment


def _read_cloud_settings(
    **overrides: str,
) -> dict[str, Any]:
    """Read cloud settings in a separate process."""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            PRODUCTION_SETTINGS_SCRIPT,
        ],
        cwd=ROOT_DIR,
        env=_cloud_environment(**overrides),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    return json.loads(completed.stdout)


def test_render_repository_files_are_safe() -> None:
    """Render files should use the validated production runtime."""
    requirements = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8")
    python_version = (ROOT_DIR / ".python-version").read_text(encoding="utf-8")
    build_script = (ROOT_DIR / "scripts/render_build.sh").read_text(encoding="utf-8")
    blueprint = (ROOT_DIR / "render.yaml").read_text(encoding="utf-8")

    assert requirements.strip() == ("-r requirements/production.txt")
    assert python_version.strip() == "3.13.14"

    assert "collectstatic --noinput --clear" in build_script
    assert "migrate --noinput" in build_script

    assert "plan: free" in blueprint
    assert "runtime: python" in blueprint
    assert "healthCheckPath: /health/live/" in blueprint
    assert "DATABASE_URL" in blueprint
    assert "R2_SECRET_ACCESS_KEY" in blueprint

    assert "AdminDemo123!" not in blueprint
    assert "DATABASE_URL=" not in blueprint


def test_neon_database_url_overrides_split_variables() -> None:
    """Neon should configure PostgreSQL from DATABASE_URL."""
    settings = _read_cloud_settings()
    database = settings["database"]

    assert settings["allowed_hosts"] == ["oyera-auto-service-system.onrender.com"]
    assert database["ENGINE"] == ("django.db.backends.postgresql")
    assert database["NAME"] == "oyera_test"
    assert database["USER"] == "oyera_test"
    assert database["HOST"] == ("ep-example.eu-central-1.aws.neon.tech")
    assert database["CONN_MAX_AGE"] == 60
    assert database["CONN_HEALTH_CHECKS"] is True
    assert database["OPTIONS"]["sslmode"] == "require"
    assert database["OPTIONS"]["channel_binding"] == "require"


def test_r2_storage_is_environment_controlled() -> None:
    """R2 should remain private and use scoped credentials."""
    settings = _read_cloud_settings(
        USE_R2_STORAGE="true",
        R2_ACCESS_KEY_ID="test-access-key",
        R2_SECRET_ACCESS_KEY="test-secret-key",
        R2_BUCKET_NAME="oyera-media",
        R2_ENDPOINT_URL=("https://example.r2.cloudflarestorage.com"),
    )

    storage = settings["default_storage"]

    assert storage["BACKEND"] == ("storages.backends.s3.S3Storage")
    assert storage["OPTIONS"] == {
        "access_key": "test-access-key",
        "secret_key": "test-secret-key",
        "bucket_name": "oyera-media",
        "endpoint_url": ("https://example.r2.cloudflarestorage.com"),
        "region_name": "auto",
        "location": "media",
        "default_acl": None,
        "file_overwrite": False,
        "querystring_auth": True,
    }


def test_gunicorn_uses_render_port(
    monkeypatch,
) -> None:
    """Render's assigned PORT should control Gunicorn."""
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.delenv(
        "GUNICORN_BIND",
        raising=False,
    )

    configuration = runpy.run_path(str(ROOT_DIR / "gunicorn.conf.py"))

    assert configuration["bind"] == "0.0.0.0:10000"
