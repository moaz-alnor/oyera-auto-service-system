# OYERA Senior Technician Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | Senior Technician |
| Username | `senior_technician` |
| Password | `SeniorTechDemo123!` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/senior-technician/` |

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

## Exact Senior Technician procedures

## Senior Technician UAT

Reset the database, then log in as `senior_technician`.

### UAT-SEN-01 — Reserve required stock

1. Open `/inventory/requirements/1/reserve/`.
2. Confirm vehicle `UAT 101A`.
3. Select:
   `OIL-FILTER-001 - Engine oil filter -
   Main Parts Store`.
4. Enter quantity: `1.000`.
5. Submit.

Expected:

- An active reservation is created.
- Requirement status becomes `RESERVED`.
- Reserved stock increases by `1.000`.

Evidence: requirement and inventory screenshots.

Result: __________

### UAT-SEN-02 — Issue reserved stock

1. Open `/inventory/reservations/1/issue/`.
2. Enter:
   - Quantity: `1.000`
   - Notes: `Issued during Senior Technician UAT.`
3. Leave occurrence time blank.
4. Submit.

Expected:

- Issue movement is created.
- Reservation becomes partially issued.
- Requirement status becomes `PARTIALLY_ISSUED`.

Evidence: reservation and movement screenshots.

Result: __________

### UAT-SEN-03 — Return issued stock

1. Open `/inventory/movements/4/return/`.
2. Enter:
   - Quantity: `0.500`
   - Notes: `Unused filter quantity returned during UAT.`
3. Leave occurrence time blank.
4. Submit.

Expected:

- Return movement is created.
- On-hand stock increases by `0.500`.
- Return does not exceed the original `1.500` issue.

Evidence: movement and inventory screenshots.

Result: __________

### UAT-SEN-04 — Start, hold, and resume work order

1. Open `/workshop/2/start/` and start the order.
2. Confirm status `IN_PROGRESS`.
3. Open `/workshop/2/hold/`.
4. Enter:
   `UAT pause while confirming workshop equipment.`
5. Submit and confirm status `ON_HOLD`.
6. Open `/workshop/2/resume/`.
7. Resume and confirm status `IN_PROGRESS`.

Evidence: screenshots of all three statuses.

Result: __________

### UAT-SEN-05 — Add workshop note

1. Open `/workshop/tasks/2/notes/new/`.
2. Select note type `Technical`.
3. Enter:
   `Senior Technician verified the assigned UAT task.`
4. Save.

Expected:

- Append-only task note is visible with author and timestamp.

Evidence: task-note screenshot.

Result: __________

### UAT-SEN-06 — Billing is forbidden

1. Open `http://127.0.0.1:8000/billing/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

## Verified execution results

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-SEN-01 | PASS | `evidence/senior-technician/UAT-SEN-01-stock-reserved.png` |  | UAT 101A stock was reserved by senior_technician. |
| UAT-SEN-02 | PASS | `evidence/senior-technician/UAT-SEN-02-stock-issued.png` |  | UAT 202B reservation became PARTIALLY_ISSUED. |
| UAT-SEN-03 | PASS | `evidence/senior-technician/UAT-SEN-03-stock-returned.png` |  | A 0.500 stock return was recorded for UAT 303C. |
| UAT-SEN-04 | PASS | `evidence/senior-technician/UAT-SEN-04a-work-order-started.png`, `UAT-SEN-04b-work-order-held.png`, and `UAT-SEN-04c-work-order-resumed.png` |  | UAT 202B completed the start, hold, and resume cycle. |
| UAT-SEN-05 | PASS | `evidence/senior-technician/UAT-SEN-05-technical-note-added.png` |  | An append-only TECHNICAL task note was recorded. |
| UAT-SEN-06 | PASS | `evidence/senior-technician/UAT-SEN-06-billing-denied.png` |  | Senior Technician billing access correctly returned HTTP 403. |

## CSV evidence

No CSV evidence is required for this role.

## Tester completion record

| Field | Entry |
| --- | --- |
| Tester | |
| Test date | |
| Environment | |
| Result | PASS / FAIL / BLOCKED |
| Defect IDs | |
| Signature | |
