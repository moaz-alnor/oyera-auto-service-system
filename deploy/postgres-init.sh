#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_ADMIN_USER:?POSTGRES_ADMIN_USER is required}"
: "${OYERA_APP_DB_USER:?OYERA_APP_DB_USER is required}"
: "${OYERA_APP_DB_PASSWORD:?OYERA_APP_DB_PASSWORD is required}"

psql \
    --set ON_ERROR_STOP=1 \
    --username "$POSTGRES_ADMIN_USER" \
    --dbname "$POSTGRES_DB" \
    --set app_user="$OYERA_APP_DB_USER" \
    --set app_password="$OYERA_APP_DB_PASSWORD" \
    --set db_name="$POSTGRES_DB" <<'SQL'
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'app_user',
    :'app_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'app_user'
)
\gexec

SELECT format(
    'ALTER ROLE %I WITH '
    'NOSUPERUSER NOCREATEDB NOCREATEROLE '
    'NOREPLICATION NOBYPASSRLS',
    :'app_user'
)
\gexec

SELECT format(
    'ALTER DATABASE %I OWNER TO %I',
    :'db_name',
    :'app_user'
)
\gexec

SELECT format(
    'ALTER SCHEMA public OWNER TO %I',
    :'app_user'
)
\gexec

SELECT format(
    'GRANT ALL ON SCHEMA public TO %I',
    :'app_user'
)
\gexec
SQL
