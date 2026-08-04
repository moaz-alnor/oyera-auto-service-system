#!/usr/bin/env bash
set -euo pipefail

umask 077

usage() {
    cat <<'EOF'
Usage:
  scripts/db_restore.sh BACKUP_FILE TARGET_DATABASE

The safe default creates a new target database.

Required application environment variables:
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD

Optional application connection variables:
  POSTGRES_HOST                  Default: 127.0.0.1
  POSTGRES_PORT                  Default: 5432
  PGCONNECT_TIMEOUT              Default: 10

Optional administrator connection:
  POSTGRES_ADMIN_HOST            Default: POSTGRES_HOST
  POSTGRES_ADMIN_PORT            Default: POSTGRES_PORT
  POSTGRES_ADMIN_USER            Default: POSTGRES_USER
  POSTGRES_ADMIN_PASSWORD        Default: POSTGRES_PASSWORD
  POSTGRES_MAINTENANCE_DB        Default: postgres

Replacing an existing target requires both:
  OYERA_RESTORE_REPLACE_EXISTING=true
  OYERA_RESTORE_CONFIRM_DATABASE=<exact target database>

Targeting the configured POSTGRES_DB additionally requires both:
  OYERA_ALLOW_PRODUCTION_RESTORE=true
  OYERA_PRODUCTION_RESTORE_CONFIRM=<exact target database>
EOF
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 ||
        fail "Required command is not installed: $1"
}

require_environment() {
    variable_name="$1"

    if test -z "${!variable_name:-}"; then
        fail "Required environment variable is missing: ${variable_name}"
    fi
}

if test "$#" -ne 2; then
    usage >&2
    exit 2
fi

archive_file="$1"
target_database="$2"

require_environment POSTGRES_DB
require_environment POSTGRES_USER
require_environment POSTGRES_PASSWORD

POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-10}"

POSTGRES_ADMIN_HOST="${POSTGRES_ADMIN_HOST:-$POSTGRES_HOST}"
POSTGRES_ADMIN_PORT="${POSTGRES_ADMIN_PORT:-$POSTGRES_PORT}"
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-$POSTGRES_USER}"
POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD-$POSTGRES_PASSWORD}"
POSTGRES_MAINTENANCE_DB="${POSTGRES_MAINTENANCE_DB:-postgres}"

case "$target_database" in
    postgres|template0|template1)
        fail \
            "Refusing to restore into protected system database: " \
            "${target_database}"
        ;;
esac

if ! printf '%s' "$target_database" |
    grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$'
then
    fail \
        "Target database must contain only letters, numbers, and " \
        "underscores, and must not begin with a number."
fi

if ! test -f "$archive_file"; then
    fail "Backup archive does not exist: ${archive_file}"
fi

if test "$target_database" = "$POSTGRES_DB"; then
    if test "${OYERA_ALLOW_PRODUCTION_RESTORE:-false}" != "true"; then
        fail \
            "Refusing to restore into configured database " \
            "${POSTGRES_DB}. Set OYERA_ALLOW_PRODUCTION_RESTORE=true " \
            "and provide the exact confirmation variable."
    fi

    if test "${OYERA_PRODUCTION_RESTORE_CONFIRM:-}" != \
        "$target_database"
    then
        fail \
            "OYERA_PRODUCTION_RESTORE_CONFIRM must exactly match " \
            "${target_database}."
    fi
fi

require_command psql
require_command pg_restore
require_command createdb
require_command dropdb

export PGCONNECT_TIMEOUT

# Validate the archive before creating or deleting any database.
pg_restore \
    --list \
    "$archive_file" \
    >/dev/null

database_exists="$(
    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" \
    psql \
        --host "$POSTGRES_ADMIN_HOST" \
        --port "$POSTGRES_ADMIN_PORT" \
        --username "$POSTGRES_ADMIN_USER" \
        --dbname "$POSTGRES_MAINTENANCE_DB" \
        --no-password \
        --quiet \
        --tuples-only \
        --no-align \
        --command \
        "SELECT 1
         FROM pg_database
         WHERE datname = '${target_database}';" \
        | tr -d '[:space:]'
)"

if test "$database_exists" = "1"; then
    if test "${OYERA_RESTORE_REPLACE_EXISTING:-false}" != "true"; then
        fail \
            "Target database already exists: ${target_database}. " \
            "Restoring over it is disabled by default."
    fi

    if test "${OYERA_RESTORE_CONFIRM_DATABASE:-}" != \
        "$target_database"
    then
        fail \
            "OYERA_RESTORE_CONFIRM_DATABASE must exactly match " \
            "${target_database}."
    fi

    printf 'Dropping explicitly confirmed target database: %s\n' \
        "$target_database"

    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" \
    dropdb \
        --host "$POSTGRES_ADMIN_HOST" \
        --port "$POSTGRES_ADMIN_PORT" \
        --username "$POSTGRES_ADMIN_USER" \
        --no-password \
        --force \
        "$target_database"
fi

created_database=false
restore_completed=false

cleanup() {
    status="$?"

    if test "$restore_completed" != "true" &&
        test "$created_database" = "true"
    then
        printf \
            'Restore failed; removing incomplete target database: %s\n' \
            "$target_database" \
            >&2

        PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" \
        dropdb \
            --host "$POSTGRES_ADMIN_HOST" \
            --port "$POSTGRES_ADMIN_PORT" \
            --username "$POSTGRES_ADMIN_USER" \
            --no-password \
            --if-exists \
            --force \
            "$target_database" \
            >/dev/null 2>&1 || true
    fi

    exit "$status"
}

trap cleanup EXIT INT TERM

PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" \
createdb \
    --host "$POSTGRES_ADMIN_HOST" \
    --port "$POSTGRES_ADMIN_PORT" \
    --username "$POSTGRES_ADMIN_USER" \
    --no-password \
    --owner "$POSTGRES_USER" \
    "$target_database"

created_database=true

# Restore application objects using the restricted OYERA application role.
PGPASSWORD="$POSTGRES_PASSWORD" \
pg_restore \
    --host "$POSTGRES_HOST" \
    --port "$POSTGRES_PORT" \
    --username "$POSTGRES_USER" \
    --dbname "$target_database" \
    --no-password \
    --exit-on-error \
    --single-transaction \
    --no-owner \
    --no-privileges \
    "$archive_file"

restore_completed=true
trap - EXIT INT TERM

printf 'Backup restored successfully into database:\n%s\n' \
    "$target_database"
