#!/usr/bin/env bash
set -euo pipefail

umask 077

usage() {
    cat <<'EOF'
Usage:
  scripts/db_backup.sh [OUTPUT_FILE]

Required environment variables:
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD

Optional environment variables:
  POSTGRES_HOST             Default: 127.0.0.1
  POSTGRES_PORT             Default: 5432
  PGCONNECT_TIMEOUT         Default: 10
  OYERA_BACKUP_DIR          Default: backups
  OYERA_BACKUP_OVERWRITE    Set to true to replace an existing output file
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

if test "$#" -gt 1; then
    usage >&2
    exit 2
fi

require_command pg_dump
require_command pg_restore

require_environment POSTGRES_DB
require_environment POSTGRES_USER
require_environment POSTGRES_PASSWORD

POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-10}"

if test "$#" -eq 1; then
    output_file="$1"
else
    backup_directory="${OYERA_BACKUP_DIR:-backups}"
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    output_file="${backup_directory}/oyera-${POSTGRES_DB}-${timestamp}.dump"
fi

if test -e "$output_file" &&
    test "${OYERA_BACKUP_OVERWRITE:-false}" != "true"
then
    fail \
        "Backup file already exists: ${output_file}. " \
        "Set OYERA_BACKUP_OVERWRITE=true to replace it."
fi

output_directory="$(dirname "$output_file")"
mkdir -p "$output_directory"

partial_file="${output_file}.partial.$$"

cleanup() {
    rm -f "$partial_file"
}

trap cleanup EXIT INT TERM

export PGPASSWORD="$POSTGRES_PASSWORD"
export PGCONNECT_TIMEOUT

pg_dump \
    --host "$POSTGRES_HOST" \
    --port "$POSTGRES_PORT" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --no-password \
    --format custom \
    --no-owner \
    --no-privileges \
    --file "$partial_file"

pg_restore \
    --list \
    "$partial_file" \
    >/dev/null

mv "$partial_file" "$output_file"
chmod 600 "$output_file"

trap - EXIT INT TERM

printf 'Backup created and validated:\n%s\n' "$output_file"
