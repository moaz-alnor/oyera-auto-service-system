"""Behavioral tests for database backup and restore scripts."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT_DIR / "scripts" / "db_backup.sh"
RESTORE_SCRIPT = ROOT_DIR / "scripts" / "db_restore.sh"


def _write_executable(path: Path, content: str) -> None:
    """Create one executable fake command."""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _operation_environment(
    tmp_path: Path,
) -> tuple[dict[str, str], Path]:
    """Create fake PostgreSQL commands and a test environment."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    fake_log = tmp_path / "commands.log"

    _write_executable(
        fake_bin / "pg_dump",
        """#!/usr/bin/env bash
set -eu

output_file=""

while test "$#" -gt 0; do
    case "$1" in
        --file)
            output_file="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

test -n "$output_file"

printf 'fake custom archive\\n' > "$output_file"
printf 'pg_dump\\n' >> "$FAKE_LOG"
""",
    )

    _write_executable(
        fake_bin / "pg_restore",
        """#!/usr/bin/env bash
set -eu

printf 'pg_restore %s\\n' "$*" >> "$FAKE_LOG"
exit 0
""",
    )

    _write_executable(
        fake_bin / "psql",
        """#!/usr/bin/env bash
set -eu

printf 'psql %s\\n' "$*" >> "$FAKE_LOG"
printf '%s\\n' "${FAKE_DB_EXISTS:-}"
""",
    )

    _write_executable(
        fake_bin / "createdb",
        """#!/usr/bin/env bash
set -eu

printf 'createdb %s\\n' "$*" >> "$FAKE_LOG"
""",
    )

    _write_executable(
        fake_bin / "dropdb",
        """#!/usr/bin/env bash
set -eu

printf 'dropdb %s\\n' "$*" >> "$FAKE_LOG"
""",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": (f"{fake_bin}{os.pathsep}{environment['PATH']}"),
            "POSTGRES_DB": "oyera_protected",
            "POSTGRES_USER": "oyera_test",
            "POSTGRES_PASSWORD": "test-password",
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "POSTGRES_ADMIN_HOST": "admin.socket",
            "POSTGRES_ADMIN_PORT": "6543",
            "FAKE_LOG": str(fake_log),
        }
    )

    return environment, fake_log


def test_database_scripts_have_valid_bash_syntax() -> None:
    """Both operation scripts should parse as valid Bash."""
    for script in (BACKUP_SCRIPT, RESTORE_SCRIPT):
        completed = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr


def test_backup_creates_validated_private_archive(
    tmp_path: Path,
) -> None:
    """The backup script should validate and protect its output."""
    environment, fake_log = _operation_environment(tmp_path)
    archive = tmp_path / "oyera.dump"

    completed = subprocess.run(
        [
            "bash",
            str(BACKUP_SCRIPT),
            str(archive),
        ],
        cwd=ROOT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert archive.read_text(encoding="utf-8") == ("fake custom archive\n")
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600

    command_log = fake_log.read_text(encoding="utf-8")

    assert "pg_dump" in command_log
    assert "pg_restore --list" in command_log


def test_backup_refuses_to_overwrite_existing_archive(
    tmp_path: Path,
) -> None:
    """An existing backup must not be replaced without opt-in."""
    environment, _fake_log = _operation_environment(tmp_path)

    archive = tmp_path / "existing.dump"
    archive.write_text(
        "keep this archive\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "bash",
            str(BACKUP_SCRIPT),
            str(archive),
        ],
        cwd=ROOT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "already exists" in completed.stderr
    assert archive.read_text(encoding="utf-8") == ("keep this archive\n")


def test_restore_creates_new_database_and_restores_archive(
    tmp_path: Path,
) -> None:
    """A normal restore should target a newly created database."""
    environment, fake_log = _operation_environment(tmp_path)

    archive = tmp_path / "source.dump"
    archive.write_text(
        "fake archive\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "bash",
            str(RESTORE_SCRIPT),
            str(archive),
            "oyera_restore_test",
        ],
        cwd=ROOT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    command_log = fake_log.read_text(encoding="utf-8")

    assert "createdb" in command_log
    assert "oyera_restore_test" in command_log
    assert "pg_restore --list" in command_log
    assert "--single-transaction" in command_log
    assert ":'target_database'" not in command_log
    assert "datname = 'oyera_restore_test'" in command_log
    assert "--owner oyera_test" in command_log
    assert "--host admin.socket" in command_log
    assert "--port 6543" in command_log


def test_restore_refuses_configured_database_without_confirmation(
    tmp_path: Path,
) -> None:
    """The configured database must receive extra protection."""
    environment, _fake_log = _operation_environment(tmp_path)

    archive = tmp_path / "source.dump"
    archive.write_text(
        "fake archive\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "bash",
            str(RESTORE_SCRIPT),
            str(archive),
            "oyera_protected",
        ],
        cwd=ROOT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Refusing to restore into configured database" in completed.stderr


def test_restore_refuses_existing_database_without_confirmation(
    tmp_path: Path,
) -> None:
    """Existing targets must not be replaced by default."""
    environment, _fake_log = _operation_environment(tmp_path)
    environment["FAKE_DB_EXISTS"] = "1"

    archive = tmp_path / "source.dump"
    archive.write_text(
        "fake archive\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "bash",
            str(RESTORE_SCRIPT),
            str(archive),
            "oyera_existing",
        ],
        cwd=ROOT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "already exists" in completed.stderr
