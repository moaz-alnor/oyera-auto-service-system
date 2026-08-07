# Contributing to OYERA

OYERA favors small, reviewable changes with explicit tests and documented operational impact.

## Workflow

1. Synchronize `main`.
2. Create a focused branch.
3. Make one coherent change.
4. Add or update tests.
5. Run the quality gate.
6. Open a pull request.
7. Merge only after required checks pass.

Recommended branch names:

```text
feature/<short-description>
fix/<short-description>
docs/<short-description>
chore/<short-description>
security/<short-description>
```

## Commit messages

Use Conventional Commit-style messages where practical:

```text
feat(accounts): add employee password reset
fix(inventory): prevent duplicate stock issue
test(uat): cover cashier payment workflow
docs(readme): document cloud architecture
chore(deploy): update Render runtime
security(auth): tighten session settings
```

## Quality gate

```bash
ruff check src tests scripts gunicorn.conf.py
ruff format --check src tests scripts gunicorn.conf.py
bash -n scripts/db_backup.sh scripts/db_restore.sh
python src/manage.py makemigrations --check --dry-run
python src/manage.py check
python -m pip check
pytest
```

## Database changes

Model changes should include a reviewed migration and tests. Do not edit historical migrations without a reviewed reason.

## Tests

New behavior should normally include tests covering business rules, permissions, state transitions, failure conditions, persistence, and deployment configuration where relevant.

## Security

Never commit `.env` files, database URLs, passwords, API tokens, Render secrets, Neon credentials, Cloudflare R2 keys, customer data, or production data.

Security vulnerabilities must not be reported publicly. Follow [SECURITY.md](SECURITY.md).

## Pull requests

Explain what changed, why it is needed, how it was tested, and any database, deployment, security, or UI impact.

## Documentation

Update documentation whenever a change affects setup, permissions, environment variables, deployment, backup/restore, operations, or user workflows.
