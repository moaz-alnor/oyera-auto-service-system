# OYERA Database Backup and Restore Guide

## Purpose

OYERA provides controlled PostgreSQL backup and restoration scripts:

- `scripts/db_backup.sh` creates and validates a backup archive.
- `scripts/db_restore.sh` restores an archive into a controlled target.

Backups may contain employee, customer, supplier, vehicle, financial,
inventory, purchasing, and workshop information. They must be treated as
confidential.

## Required tools

The workstation performing the operation requires:

- `pg_dump`
- `pg_restore`
- `psql`
- `createdb`
- `dropdb`

## Application database variables

The scripts use:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

The host defaults to `127.0.0.1`, and the port defaults to `5432`.

## Optional administrator connection

A production application role should not normally require permission to
create or delete databases. Database lifecycle operations can therefore use:

- `POSTGRES_ADMIN_HOST`
- `POSTGRES_ADMIN_PORT`
- `POSTGRES_ADMIN_USER`
- `POSTGRES_ADMIN_PASSWORD`

The administrator host and port default to the application database host and
port. The administrator user and password default to the application
credentials.

The administrator creates the target database and assigns ownership to
`POSTGRES_USER`. The archive itself is restored using the application role.

## Create a backup

Create a timestamped archive:

    scripts/db_backup.sh

Create an archive at a specific location:

    scripts/db_backup.sh /secure/location/oyera-production.dump

The backup script:

1. Uses PostgreSQL custom format.
2. Excludes ownership and privilege restoration.
3. Writes to a temporary partial file.
4. Validates the archive with `pg_restore --list`.
5. Applies file permission mode `600`.
6. Refuses to overwrite existing archives by default.

Intentional overwrite requires:

    OYERA_BACKUP_OVERWRITE=true

## Restore into a separate database

The normal verification method is:

    scripts/db_restore.sh \
      /secure/location/oyera-production.dump \
      oyera_restore_verification

The script validates the archive before creating or replacing a database.

## Existing-target protection

Replacing an existing database requires both:

    OYERA_RESTORE_REPLACE_EXISTING=true
    OYERA_RESTORE_CONFIRM_DATABASE=<exact target name>

## Configured-database protection

Restoring into the database named by `POSTGRES_DB` additionally requires:

    OYERA_ALLOW_PRODUCTION_RESTORE=true
    OYERA_PRODUCTION_RESTORE_CONFIRM=<exact target name>

All confirmation values must exactly match the selected target database.

## Verification requirements

After restoring into a separate database:

1. Compare public-table counts.
2. Compare Django migration counts.
3. Compare representative business-record counts.
4. Run Django system and migration checks.
5. Test representative role workflows.
6. Delete the verification database after acceptance.

A backup is not considered reliable until a real restoration test succeeds.

## Storage rules

- Never commit backup archives to Git.
- Keep credentials outside the scripts.
- Store production backups outside the application server.
- Use approved encrypted storage.
- Restrict access to authorized administrators.
- Define retention and secure-deletion rules.
