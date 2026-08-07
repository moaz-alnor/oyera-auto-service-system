# Changelog

Significant changes to OYERA Auto Service System are recorded here.

The project uses semantic versioning for published releases.

## [Unreleased]

## [1.0.0] - 2026-08-07

### Added

- Complete customer and vehicle records with ownership tracking.
- Quotation, job-card, workshop, technician-assignment, and task workflows.
- Inventory reservation, issue, return, movement, and stock-control workflows.
- Product and service catalogues with pricing support.
- Purchasing workflows covering suppliers, purchase orders, goods receipts, supplier invoices, and supplier payments.
- Customer billing, invoice, payment, and vehicle-release workflows.
- Operational reports and CSV exports.
- Six-role access-control model for Administrator, Manager, Receptionist, Senior Technician, Technician, and Cashier.
- Role-by-role browser UAT evidence and final handover documentation.
- Public repository documentation, contribution standards, issue templates, and security policy.

### Security

- Production security hardening for HTTPS-aware deployments, secure cookies, allowed hosts, and environment-managed secrets.
- Automated dependency auditing with `pip-audit`.
- Python security scanning with Bandit.
- GitHub CodeQL analysis, Dependabot, secret scanning, and push protection.
- Controlled and auditable authorization for business-critical operations.

### Deployment

- Managed cloud deployment support for Render and Neon PostgreSQL.
- Cloudflare R2-compatible S3 media-storage configuration.
- Docker-based production deployment with PostgreSQL and Caddy as an alternative deployment path.
- Gunicorn production runtime and WhiteNoise static-file delivery.
- Liveness and database-readiness health endpoints.
- Database backup and protected restore tooling.

### Validation

- **32/32 role-based UAT cases passed**.
- **41 screenshot evidence files** and **10 CSV evidence files** retained in the handover package.
- Full automated test suite and required GitHub CI/security checks passing at release preparation.

## Release policy

Future published releases use:

```text
## [x.y.z] - YYYY-MM-DD
```

Group changes under `Added`, `Changed`, `Fixed`, `Security`, `Deprecated`, and `Removed` as appropriate.
