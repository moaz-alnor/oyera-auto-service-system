# Development Guide

## Prerequisites

- Python 3.13
- PostgreSQL
- Git
- optional Docker/Colima for container validation

## Setup

```bash
git clone https://github.com/moaz-alnor/oyera-auto-service-system.git
cd oyera-auto-service-system

python3.13 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements/development.txt

cp .env.example .env
```

Configure local PostgreSQL values in `.env`, then:

```bash
python src/manage.py migrate
python src/manage.py seed_roles
python src/manage.py createsuperuser
python src/manage.py runserver
```

## Demo/UAT data

Demo credentials and reset tooling are for local testing only. Never reuse demo passwords in production or run destructive demo reset commands against production data.

## Quality

```bash
ruff check src tests scripts gunicorn.conf.py
ruff format src tests scripts gunicorn.conf.py
git diff --check
```

## Django checks

```bash
python src/manage.py makemigrations --check --dry-run
python src/manage.py check
```

## Tests

```bash
pytest
```

## Branch workflow

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/short-description
```

Before pushing, run the relevant quality gate and confirm no credentials or production data are present.

## Database operations

See [operations/database-backup-restore.md](operations/database-backup-restore.md).

## Production

Production settings are environment-driven. Never hard-code cloud credentials, passwords, or secret-bearing URLs.
