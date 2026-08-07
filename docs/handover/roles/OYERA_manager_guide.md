# OYERA Manager Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | Manager |
| Username | `manager` |
| Password | `ManagerDemo123!` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/manager/` |

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

## Exact Manager procedures

## Manager UAT

Reset the database, then log in as `manager`.

### UAT-MGR-01 — Authentication and dashboard

Expected:

- Login succeeds.
- Operational modules and reports are visible.
- Django administration is not available as a normal Manager function.

Evidence: dashboard screenshot.

Result: __________

### UAT-MGR-02 — Reports and CSV exports

Repeat all report and export URLs from UAT-ADM-03.

Expected:

- All report pages and CSV exports succeed.

Evidence: one screenshot per report and exported files.

Result: __________

### UAT-MGR-03 — Approve purchase order

1. Open `/purchasing/purchase-orders/2/approve/`.
2. Confirm `DEMO-PO-SUBMITTED`.
3. Tick the approval confirmation.
4. Submit.

Expected:

- Status becomes `APPROVED`.

Evidence: final status screenshot.

Result: __________

### UAT-MGR-04 — Authorise unpaid vehicle release

1. Open `/jobs/5/release/`.
2. Confirm vehicle registration `UAT 505E`.
3. Enter:
   - Final mileage: `50500`
   - Final vehicle condition:
     `Vehicle ready for controlled UAT release.`
   - Received by:
     `UAT Manager Receiver`
   - Receiver contact:
     `+256700000505`
   - Handover notes:
     `Keys and documents handed over during UAT.`
4. Tick:
   `Authorise release with outstanding balance`.
5. Enter override reason:
   `Manager-approved UAT customer credit exception.`
6. Submit.

Expected:

- Release succeeds.
- Vehicle/job status becomes `RELEASED`.
- The outstanding invoice remains recorded.
- The override reason and approving Manager are auditable.

Evidence: release-detail screenshot and invoice balance screenshot.

Result: __________

### UAT-MGR-05 — Manager cannot enter Django administration

1. Open `http://127.0.0.1:8000/admin/`.

Expected:

- The Django administration index does not open.
- The user is redirected to the admin login page because the Manager
  is not a staff administrator.

Evidence: redirected URL screenshot.

Result: __________

## Verified execution results

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-MGR-01 | PASS | `evidence/manager/UAT-MGR-01-dashboard.png` |  | Automated Manager login and dashboard verification passed. |
| UAT-MGR-02 | PASS | `evidence/manager/` and `evidence/csv/` |  | Four Manager report pages and four CSV exports passed. |
| UAT-MGR-03 | PASS | `evidence/manager/UAT-MGR-03-purchase-order-approved.png` |  | DEMO-PO-SUBMITTED was approved by manager. |
| UAT-MGR-04 | PASS | `evidence/manager/UAT-MGR-04-unpaid-release-approved.png` |  | UAT 505E was released with a Manager payment override and outstanding balance. |
| UAT-MGR-05 | PASS | `evidence/manager/UAT-MGR-05-admin-denied.png` |  | Manager was redirected to the Django admin login page. |

## CSV evidence

- `docs/uat/evidence/csv/UAT-MGR-02-customer-finance.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-inventory-activity.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-purchasing-activity.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-workshop-operations.csv`

## Tester completion record

| Field | Entry |
| --- | --- |
| Tester | |
| Test date | |
| Environment | |
| Result | PASS / FAIL / BLOCKED |
| Defect IDs | |
| Signature | |
