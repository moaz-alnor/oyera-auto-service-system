# OYERA Production Deployment Guide

## Architecture

The production deployment contains three services:

1. `caddy` terminates HTTPS and serves uploaded media.
2. `app` runs Django through Gunicorn as a non-root user.
3. `db` runs PostgreSQL on an internal-only network.

Only Caddy publishes ports to the host. The application and database are not
directly exposed to the public network.

## Server requirements

Install:

- Docker Engine or Docker Desktop
- Docker Compose
- Git

For a public deployment:

- The domain must resolve to the server.
- TCP ports 80 and 443 must be reachable.
- The server must have persistent storage for Docker volumes.

## Create the production environment

Copy the template:

    cp .env.production.example .env.production

Generate three separate secrets:

    python - <<'PY'
    import secrets

    for name in (
        "DJANGO_SECRET_KEY",
        "POSTGRES_ADMIN_PASSWORD",
        "POSTGRES_PASSWORD",
    ):
        print(f"{name}={secrets.token_urlsafe(48)}")
    PY

Place the generated values in `.env.production`.

Never use the demonstration usernames or passwords in production.

## Validate the configuration

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      config --quiet

## Start the stack

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      up \
      --detach \
      --build

The application startup process:

1. Runs the Django system check.
2. Applies database migrations.
3. Collects static files.
4. Starts Gunicorn.

## Check service state

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      ps

All three services should be running. The database and application should
report a healthy status.

## Verify health endpoints

    curl --fail https://your-domain.example/health/live/

    curl --fail https://your-domain.example/health/ready/

The liveness endpoint confirms that the web process is available. The
readiness endpoint also confirms database connectivity.

## Inspect logs

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      logs \
      --tail 200

## Run the deployment security check

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      exec \
      --no-TTY \
      app \
      python src/manage.py check \
        --deploy \
        --fail-level WARNING

The command must report no warnings before acceptance.

## Create the first administrator

Do not run `reset_demo_data` in production.

Create the initial administrator interactively:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      exec app \
      python src/manage.py createsuperuser

Create ordinary employees through the OYERA employee-management interface and
assign each employee the minimum required role.

## HSTS rollout

Keep `DJANGO_SECURE_HSTS_SECONDS=0` during initial HTTPS verification.

After HTTPS, proxy handling, the domain, and intended subdomains are verified:

1. Begin with a short HSTS duration.
2. Observe the production deployment.
3. Increase the duration gradually.
4. Enable subdomains only when every subdomain supports HTTPS.
5. Enable preload only after permanent HTTPS readiness is confirmed.

## Persistent data

The following Docker volumes contain persistent information:

- `postgres_data`: PostgreSQL database
- `media_data`: user-uploaded files
- `caddy_data`: TLS certificates and Caddy state
- `caddy_config`: Caddy runtime configuration

Do not delete these volumes during routine deployment or shutdown.

## Database backup

Create a backup directory:

    mkdir -p backups

Create the database archive:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      exec \
      --no-TTY \
      app \
      scripts/db_backup.sh \
        /tmp/oyera-production.dump

Copy it to the host:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      cp \
      app:/tmp/oyera-production.dump \
      backups/oyera-production.dump

Store database archives as confidential information.

Uploaded media must be backed up separately from PostgreSQL.

## Application update

Before every update:

1. Create and validate a database backup.
2. Back up uploaded media.
3. Pull the reviewed release.
4. Rebuild the application image.
5. Verify migrations and service health.
6. Test login and one representative role workflow.

Update command:

    git pull --ff-only

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      up \
      --detach \
      --build

## Stop the deployment

Stop containers while retaining all persistent data:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      down

Never add `--volumes` during routine production shutdown. That option deletes
the database, media, and Caddy certificate volumes.
