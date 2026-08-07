# OYERA Administrator Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | Administrator |
| Username | `admin` |
| Password | `AdminDemo123!` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/administrator/` |

> This is a local demonstration account. Replace it with a unique,
> securely managed account in production.

## Preparation and shared test rules

## OYERA Role-by-Role User Acceptance Test Casebook

- Generated: 2026-08-04
- Base URL: `http://127.0.0.1:8000`
- Database baseline: `python src/manage.py reset_demo_data --yes`
- Result fields: PASS, FAIL, or BLOCKED

### Purpose

This casebook gives the tester exact accounts, paths, input values,
expected results, forbidden results, reset steps, and evidence requirements.

### Global preparation

1. Keep the backup created before UAT.
2. Run:

       python src/manage.py reset_demo_data --yes

3. Start OYERA:

       python src/manage.py runserver 127.0.0.1:8000

4. Open `http://127.0.0.1:8000`.
5. Use a private browser window or log out between roles.
6. Reset the demo database before beginning each role section.
7. Stop immediately and record a defect if an expected result differs.

### Evidence naming

Use:

`UAT-<ROLE>-<CASE>-<short-description>.png`

Capture:

- the browser URL,
- the completed form or resulting record,
- any success or error message,
- the final status,
- downloaded CSV files where required.

### Exact demonstration accounts

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `AdminDemo123!` |
| Manager | `manager` | `ManagerDemo123!` |
| Receptionist | `receptionist` | `ReceptionDemo123!` |
| Senior Technician | `senior_technician` | `SeniorTechDemo123!` |
| Technician | `technician` | `TechnicianDemo123!` |
| Cashier | `cashier` | `CashierDemo123!` |

### Resolved seeded scenarios

| Scenario | Record | Exact path |
| --- | --- | --- |
| Submitted purchase order | `DEMO-PO-SUBMITTED` | `/purchasing/purchase-orders/2/approve/` |
| Reserve stock | `UAT 101A` | `/inventory/requirements/1/reserve/` |
| Issue stock | `UAT 202B` | `/inventory/reservations/1/issue/` |
| Return stock | `UAT 303C` | `/inventory/movements/4/return/` |
| Paid vehicle release | `UAT 404D` / invoice `1` | `/jobs/4/release/` |
| Unpaid override release | `UAT 505E` / invoice `2` | `/jobs/5/release/` |
| Customer payment | Unpaid invoice `2` | `/billing/2/payments/new/` |
| Supplier payment | `DEMO-SINV-UNPAID` | `/purchasing/supplier-invoices/2/payments/new/` |
| Assigned task A | Task `2` | `/workshop/tasks/2/start/` |
| Assigned task B | Task `3` | `/workshop/tasks/3/start/` |

## Exact Administrator procedures

## Administrator UAT

Reset the database, then log in as `admin`.

### UAT-ADM-01 — Authentication and dashboard

1. Open `http://127.0.0.1:8000/accounts/login/`.
2. Enter `admin`.
3. Enter `AdminDemo123!`.
4. Submit.

Expected:

- Login succeeds.
- Dashboard opens.
- Administration, billing, customers, inventory, jobs, products,
  purchasing, quotations, reports, services, vehicles, and workshop
  navigation are visible.

Evidence: dashboard screenshot.

Result: __________

### UAT-ADM-02 — Django administration

1. Open `http://127.0.0.1:8000/admin/`.

Expected:

- Django administration index opens.
- The account is recognised as staff and superuser.
- No permission-denied page appears.

Evidence: administration index screenshot.

Result: __________

### UAT-ADM-03 — Complete operational reporting

Open each page:

- `/reports/customer-finance/`
- `/reports/workshop-operations/`
- `/reports/inventory-activity/`
- `/reports/purchasing-activity/`

Then download:

- `/reports/customer-finance/export.csv`
- `/reports/workshop-operations/export.csv`
- `/reports/inventory-activity/export.csv`
- `/reports/purchasing-activity/export.csv`

Expected:

- All four report pages open.
- All four CSV responses download.
- CSV files contain headers and seeded rows where applicable.

Evidence: four report screenshots and four CSV files.

Result: __________

### UAT-ADM-04 — Approve submitted purchase order

1. Open `/purchasing/purchase-orders/2/approve/`.
2. Confirm the purchase order reference is `DEMO-PO-SUBMITTED`.
3. Tick:
   `I confirm that I reviewed and approve this purchase order.`
4. Submit.

Expected:

- The purchase order becomes `APPROVED`.
- Approval evidence is recorded.
- The order is no longer awaiting approval.

Evidence: approved purchase-order detail screenshot.

Result: __________

## Verified execution results

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-ADM-01 | PASS | `evidence/administrator/UAT-ADM-01-dashboard.png` |  | Automated Chrome login and dashboard navigation verification passed. |
| UAT-ADM-02 | PASS | `evidence/administrator/UAT-ADM-02-django-admin.png` |  | Django staff and superuser access passed. |
| UAT-ADM-03 | PASS | `evidence/administrator/` and `evidence/csv/` |  | Four report pages and four authenticated CSV exports passed. |
| UAT-ADM-04 | PASS | `evidence/administrator/UAT-ADM-04-purchase-order-approved.png` |  | DEMO-PO-SUBMITTED changed to APPROVED with administrator audit evidence. |

## CSV evidence

- `docs/uat/evidence/csv/UAT-ADM-03-customer-finance.csv`
- `docs/uat/evidence/csv/UAT-ADM-03-inventory-activity.csv`
- `docs/uat/evidence/csv/UAT-ADM-03-purchasing-activity.csv`
- `docs/uat/evidence/csv/UAT-ADM-03-workshop-operations.csv`

## Tester completion record

| Field | Entry |
| --- | --- |
| Tester | |
| Test date | |
| Environment | |
| Result | PASS / FAIL / BLOCKED |
| Defect IDs | |
| Signature | |
