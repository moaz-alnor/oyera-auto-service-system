ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update \
    && apt-get install \
        --yes \
        --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements/ ./requirements/

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        --requirement requirements/production.txt


FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install \
        --yes \
        --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd \
        --system \
        --gid 10001 \
        oyera \
    && useradd \
        --system \
        --uid 10001 \
        --gid oyera \
        --home-dir /home/oyera \
        --create-home \
        --shell /usr/sbin/nologin \
        oyera

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=oyera:oyera . .

RUN chmod 755 \
        scripts/container_start.sh \
        scripts/db_backup.sh \
        scripts/db_restore.sh \
        deploy/postgres-init.sh \
    && mkdir -p \
        /app/src/staticfiles \
        /var/lib/oyera/media \
    && chown -R oyera:oyera \
        /app/src/staticfiles \
        /var/lib/oyera/media

USER oyera

EXPOSE 8000

CMD ["./scripts/container_start.sh"]
