# OYERA Cashier Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | Cashier |
| Username | `cashier` |
| Password | `CashierDemo123!` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/cashier/` |

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

## Exact Cashier procedures

## Cashier UAT

Reset the database, then log in as `cashier`.

### UAT-CAS-01 — Finance reporting

Open and test:

- `/reports/customer-finance/`
- `/reports/customer-finance/export.csv`
- `/reports/purchasing-activity/`
- `/reports/purchasing-activity/export.csv`

Expected:

- Both reports open.
- Both CSV files download.
- Workshop and inventory reporting remain unavailable.

Evidence: report screenshots and CSV files.

Result: __________

### UAT-CAS-02 — Record customer payment

1. Open `/billing/2/payments/new/`.
2. Confirm the invoice belongs to vehicle `UAT 505E`.
3. Enter:
   - Amount: `10000.00`
   - Payment method: `Cash`
   - External reference: `UAT-CUSTOMER-PAY-001`
   - Notes: `Partial customer payment recorded during UAT.`
4. Leave payment time blank.
5. Submit.

Expected:

- Payment is created.
- Outstanding balance decreases by `UGX 10000.00`.
- Payment appears in invoice history.

Evidence: invoice balance and payment screenshots.

Result: __________

### UAT-CAS-03 — Record supplier payment

1. Open `/purchasing/supplier-invoices/2/payments/new/`.
2. Confirm supplier invoice reference `DEMO-SINV-UNPAID`.
3. Enter:
   - Amount: `25000.00`
   - Method: `Bank transfer`
   - External reference: `UAT-SUPPLIER-PAY-001`
   - Notes: `Partial supplier payment recorded during UAT.`
4. Leave payment time blank.
5. Submit.

Expected:

- Supplier payment is created.
- Supplier invoice becomes partially paid.
- Outstanding supplier balance decreases by `UGX 25000.00`.

Evidence: supplier-invoice and payment screenshots.

Result: __________

### UAT-CAS-04 — Workshop report is forbidden

1. Open `/reports/workshop-operations/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

### UAT-CAS-05 — Inventory report is forbidden

1. Open `/reports/inventory-activity/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

### UAT-CAS-06 — Vehicle release is forbidden

1. Open `/jobs/4/release/`.

Expected:

- Access Denied page or HTTP `403`.
- No vehicle-release record is created.

Evidence: access-denied screenshot.

Result: __________

## Verified execution results

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-CAS-01 | PASS | `evidence/cashier/` and `evidence/csv/` |  | Customer-finance and purchasing reports and CSV exports passed. |
| UAT-CAS-02 | PASS | `evidence/cashier/UAT-CAS-02-customer-payment.png` |  | A UGX 10000.00 customer payment was recorded by cashier. |
| UAT-CAS-03 | PASS | `evidence/cashier/UAT-CAS-03-supplier-payment.png` |  | A UGX 25000.00 supplier payment was recorded by cashier. |
| UAT-CAS-04 | PASS | `evidence/cashier/UAT-CAS-04-workshop-report-denied.png` |  | Cashier workshop-report access correctly returned HTTP 403. |
| UAT-CAS-05 | PASS | `evidence/cashier/UAT-CAS-05-inventory-report-denied.png` |  | Cashier inventory-report access correctly returned HTTP 403. |
| UAT-CAS-06 | PASS | `evidence/cashier/UAT-CAS-06-vehicle-release-denied.png` |  | Cashier vehicle-release access correctly returned HTTP 403. |

## CSV evidence

- `docs/uat/evidence/csv/UAT-CAS-01-customer-finance.csv`
- `docs/uat/evidence/csv/UAT-CAS-01-purchasing-activity.csv`

## Tester completion record

| Field | Entry |
| --- | --- |
| Tester | |
| Test date | |
| Environment | |
| Result | PASS / FAIL / BLOCKED |
| Defect IDs | |
| Signature | |
