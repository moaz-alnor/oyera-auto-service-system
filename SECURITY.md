# Security Policy

## Supported versions

Security fixes are applied to the current `main` branch and the latest published production release.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Use GitHub private vulnerability reporting / Security Advisories when available. If private reporting is unavailable, contact the repository owner privately through GitHub before disclosing technical details publicly.

Include a clear description, affected component, reproduction steps, impact, and proof of concept when safe.

Do not include customer data, production passwords, API keys, database URLs, or other secrets.

## Sensitive areas

Extra review is expected for authentication, authorization, sessions, passwords, payment workflows, vehicle release, inventory adjustments, database backup/restore, environment variables, cloud credentials, file storage, deployment, and logging of personal or financial data.

## Secret handling

Production secrets belong in platform environment variables or a dedicated secret-management system.

If a secret is accidentally exposed, rotate it immediately and treat it as compromised.

## Automated controls

OYERA uses `pip-audit`, Bandit, CodeQL, Dependabot, secret scanning, and push protection.
