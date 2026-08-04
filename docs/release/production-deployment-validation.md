# OYERA Production Deployment Validation

- Validation date: 2026-08-04
- Runtime: Docker Engine through Colima
- Architecture: ARM64
- Stack: Caddy, Django/Gunicorn, PostgreSQL 17
- Result: PASS

## Image validation

- Production image built successfully.
- Image tag: `oyera-auto-service:release-candidate`
- Runtime account: `uid=10001(oyera)`
- The application does not run as root.

## Service validation

- PostgreSQL became healthy.
- Django became healthy.
- Caddy started and terminated local HTTPS.
- HTTP redirected to HTTPS.
- Liveness returned HTTP 200.
- Readiness returned HTTP 200 with database status `ok`.

## Django validation

- All migrations were applied.
- Static-file collection completed.
- Gunicorn started with two workers.
- The strict deployment check passed with no warnings.
- Hardened HSTS target:
  - `SECURE_HSTS_SECONDS=31536000`
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
  - `SECURE_HSTS_PRELOAD=True`

## Database validation

- Django connected as `oyera_app`.
- Database name: `oyera_service`
- Application role permissions:
  - Superuser: false
  - Create database: false
  - Create role: false
  - Replication: false
  - Bypass row-level security: false

## Storage validation

- Hashed static asset returned HTTP 200.
- Persistent media was written by Django and read through Caddy.
- Temporary media evidence was removed.
- PostgreSQL custom-format backup was created and validated.

## Administrator validation

- A production superuser was created through `createsuperuser`.
- The account was active, staff-enabled, and a superuser.
- The temporary audit database and volumes were removed after testing.

## Acceptance

**PASS — the production container stack satisfies the Phase 17.1 deployment
and initial-setup acceptance criteria.**
