"""Regression tests for the production container deployment."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

DOCKERFILE = ROOT_DIR / "Dockerfile"
DOCKERIGNORE = ROOT_DIR / ".dockerignore"
COMPOSE = ROOT_DIR / "compose.production.yml"
ENV_EXAMPLE = ROOT_DIR / ".env.production.example"
START_SCRIPT = ROOT_DIR / "scripts" / "container_start.sh"
HEALTH_SCRIPT = ROOT_DIR / "scripts" / "container_healthcheck.py"
POSTGRES_INIT = ROOT_DIR / "deploy" / "postgres-init.sh"
CADDYFILE = ROOT_DIR / "deploy" / "Caddyfile"
CONTAINER_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "container.yml"
DEPENDABOT = ROOT_DIR / ".github" / "dependabot.yml"
DEPLOYMENT_GUIDE = ROOT_DIR / "docs" / "operations" / "production-deployment.md"


def test_dockerfile_builds_a_non_root_production_image() -> None:
    """Use production dependencies and a non-root runtime user."""
    content = DOCKERFILE.read_text(encoding="utf-8")

    assert "ARG PYTHON_VERSION=3.13" in content
    assert "python:${PYTHON_VERSION}-slim" in content
    assert "requirements/production.txt" in content
    assert "USER oyera" in content
    assert "USER root" not in content
    assert 'CMD ["./scripts/container_start.sh"]' in content


def test_docker_context_excludes_secrets_and_runtime_data() -> None:
    """Do not copy secrets, environments, media, or backups."""
    content = DOCKERIGNORE.read_text(encoding="utf-8")

    assert ".env.*" in content
    assert "!.env.production.example" in content
    assert "src/media/" in content
    assert "src/staticfiles/" in content
    assert "backups/" in content
    assert ".git" in content


def test_compose_isolates_application_and_database_services() -> None:
    """Only the HTTPS proxy should publish host ports."""
    content = COMPOSE.read_text(encoding="utf-8")

    assert "internal: true" in content
    assert 'expose:\n      - "8000"' in content
    assert "${OYERA_HTTP_PORT:-80}:80" in content
    assert "${OYERA_HTTPS_PORT:-443}:443" in content
    assert "postgres_data:/var/lib/postgresql/data" in content
    assert "media_data:/var/lib/oyera/media" in content
    assert "condition: service_healthy" in content
    assert "POSTGRES_ADMIN_USER: ${POSTGRES_ADMIN_USER}" in content


def test_start_script_runs_release_tasks_before_gunicorn() -> None:
    """Run controlled release operations before Gunicorn."""
    content = START_SCRIPT.read_text(encoding="utf-8")

    assert "OYERA_RUN_MIGRATIONS" in content
    assert "migrate --noinput" in content
    assert "collectstatic --noinput" in content
    assert "exec gunicorn" in content
    assert "runserver" not in content


def test_healthcheck_uses_liveness_and_proxy_headers() -> None:
    """Emulate the trusted HTTPS proxy during health checks."""
    content = HEALTH_SCRIPT.read_text(encoding="utf-8")

    assert '"/health/live/"' in content
    assert '"X-Forwarded-Proto": "https"' in content
    assert "DJANGO_HEALTHCHECK_HOST" in content
    assert "response.status != 200" in content


def test_database_initialization_creates_restricted_app_role() -> None:
    """Do not grant database-administrator powers to OYERA."""
    content = POSTGRES_INIT.read_text(encoding="utf-8")

    assert "CREATE ROLE" in content
    assert "NOSUPERUSER" in content
    assert "NOCREATEDB" in content
    assert "NOCREATEROLE" in content
    assert "NOREPLICATION" in content
    assert "ALTER DATABASE" in content


def test_caddy_proxies_django_and_serves_persistent_media() -> None:
    """Terminate HTTPS and serve the shared media volume."""
    content = CADDYFILE.read_text(encoding="utf-8")

    assert "{$OYERA_DOMAIN}" in content
    assert "reverse_proxy app:8000" in content
    assert "handle_path /media/*" in content
    assert "root * /srv/media" in content


def test_production_environment_example_covers_runtime_settings() -> None:
    """Document every required deployment variable."""
    content = ENV_EXAMPLE.read_text(encoding="utf-8")

    required_names = (
        "OYERA_DOMAIN=",
        "DJANGO_SECRET_KEY=",
        "DJANGO_ALLOWED_HOSTS=",
        "DJANGO_TRUST_X_FORWARDED_PROTO=true",
        "POSTGRES_ADMIN_USER=",
        "POSTGRES_ADMIN_PASSWORD=",
        "POSTGRES_USER=",
        "POSTGRES_PASSWORD=",
        "GUNICORN_WORKERS=",
        "OYERA_RUN_MIGRATIONS=",
    )

    for name in required_names:
        assert name in content

    assert "AdminDemo123!" not in content
    assert "SeniorTechDemo123!" not in content


def test_ci_and_dependabot_cover_container_deployment() -> None:
    """Automate container builds and base-image updates."""
    workflow = CONTAINER_WORKFLOW.read_text(encoding="utf-8")
    dependabot = DEPENDABOT.read_text(encoding="utf-8")

    assert "docker compose" in workflow
    assert "caddy validate" in workflow
    assert "--env OYERA_DOMAIN=localhost" in workflow
    assert "docker build" in workflow
    assert "compose.production.yml" in workflow
    assert "package-ecosystem: docker" in dependabot


def test_deployment_guide_documents_safe_operations() -> None:
    """Operators should have repeatable and safe deployment steps."""
    content = DEPLOYMENT_GUIDE.read_text(encoding="utf-8")

    normalized_content = " ".join(content.replace("\\", " ").split())

    assert "docker compose" in content
    assert "config --quiet" in normalized_content
    assert (
        "python src/manage.py check --deploy --fail-level WARNING" in normalized_content
    )
    assert "createsuperuser" in content
    assert "reset_demo_data" in content
    assert "Database backup" in content
    assert "Never add `--volumes`" in content
