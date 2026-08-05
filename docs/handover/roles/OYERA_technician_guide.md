# OYERA Technician Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | Technician |
| Username | `technician` |
| Password | `TechnicianDemo123!` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/technician/` |

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

## Exact Technician procedures

## Technician UAT

Reset the database.

### Technician preparation by Administrator

Before logging in as Technician:

1. Log in as `admin`.
2. Open `/workshop/2/start/` and start the order.
3. Open `/workshop/3/start/` and start the order.
4. Log out.
5. Log in as `technician`.

### UAT-TEC-01 — Assigned-work visibility

Expected:

- Login succeeds.
- Workshop, jobs, quotations, products, services, vehicles, and
  read-only inventory links are visible.
- Billing, purchasing finance, and reports are not visible.

Evidence: Technician dashboard screenshot.

Result: __________

### UAT-TEC-02 — Start and block assigned task

1. Open `/workshop/tasks/2/start/`.
2. Start task `2`.
3. Confirm status `IN_PROGRESS`.
4. Open `/workshop/tasks/2/block/`.
5. Enter:
   `UAT blocked while awaiting replacement seal.`
6. Submit.

Expected:

- Task status becomes `BLOCKED`.
- Blocking reason, author, and time are recorded.

Evidence: task status screenshot.

Result: __________

### UAT-TEC-03 — Complete work and submit for review

1. Open `/workshop/tasks/3/start/`.
2. Start task `3`.
3. Open `/workshop/tasks/3/review/`.
4. Enter completion notes:
   `Completed oil and filter service, checked for leaks, and verified
   normal operation during UAT.`
5. Submit.

Expected:

- Task status becomes `AWAITING_REVIEW`.
- Completion notes are retained.
- Technician cannot self-approve the task.

Evidence: awaiting-review screenshot.

Result: __________

### UAT-TEC-04 — Task approval is forbidden

1. Open `/workshop/tasks/3/approve/`.

Expected:

- Access Denied page or HTTP `403`.
- Task remains `AWAITING_REVIEW`.

Evidence: access-denied and unchanged-status screenshots.

Result: __________

### UAT-TEC-05 — Reports are forbidden

1. Open `/reports/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

## Verified execution results

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-TEC-01 | PASS | `evidence/technician/UAT-TEC-01-dashboard.png` |  | Technician login and assigned-work navigation passed. |
| UAT-TEC-02 | PASS | `evidence/technician/UAT-TEC-02-task-blocked.png` |  | Assigned UAT 202B task was started and blocked with an auditable reason. |
| UAT-TEC-03 | PASS | `evidence/technician/UAT-TEC-03-task-awaiting-review.png` |  | Assigned UAT 303C task was submitted with completion evidence. |
| UAT-TEC-04 | PASS | `evidence/technician/UAT-TEC-04-approval-rejected.png` |  | Technician self-approval was rejected; the task remained AWAITING_REVIEW. |
| UAT-TEC-05 | PASS | `evidence/technician/UAT-TEC-05-reports-denied.png` |  | Technician reports access correctly returned HTTP 403. |

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
