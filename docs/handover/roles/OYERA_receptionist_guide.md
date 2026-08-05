# OYERA Receptionist Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | Receptionist |
| Username | `receptionist` |
| Password | `ReceptionDemo123!` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/receptionist/` |

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

## Exact Receptionist procedures

## Receptionist UAT

Reset the database, then log in as `receptionist`.

### UAT-REC-01 — Register customer

1. Open `/customers/new/`.
2. Enter:
   - Customer type: `Individual`
   - Name: `UAT Reception Customer`
   - Phone number: `+256700900101`
   - Email: `uat.reception@example.com`
   - Address: `Kampala UAT Address`
   - Notes: `Created during Receptionist UAT.`
3. Save.

Expected:

- Customer is created.
- A customer number is generated.
- Customer detail page opens.

Evidence: completed customer detail screenshot.

Result: __________

### UAT-REC-02 — Register vehicle

1. Open `/vehicles/new/`.
2. Select `UAT Reception Customer`.
3. Enter:
   - Registration number: `UAT 606F`
   - Category: `Small vehicle`
   - Make: `Toyota`
   - Model: `Yaris`
   - Year: `2021`
   - Color: `Blue`
   - Current mileage: `60600`
   - Fuel type: `Petrol`
   - Notes: `Created during Receptionist UAT.`
4. Leave engine number, chassis number, and VIN blank.
5. Save.

Expected:

- Vehicle is created and linked to the selected customer.
- Registration displays as `UAT 606F`.

Evidence: vehicle-detail screenshot.

Result: __________

### UAT-REC-03 — Open job card

1. Open `/jobs/new/`.
2. Select:
   - Customer: `UAT Reception Customer`
   - Vehicle: `UAT 606F`
3. Enter:
   - Arrival mileage: `60600`
   - Customer complaint:
     `Customer reports engine oil warning during UAT.`
   - Visible condition:
     `No external damage observed during intake.`
   - Fuel level: `Half`
   - Priority: `Normal`
4. Save.

Expected:

- Job card is created with status `OPEN`.
- Customer and vehicle match.
- Mileage is accepted.

Evidence: job-card detail screenshot.

Result: __________

### UAT-REC-04 — Release fully paid vehicle

1. Open `/jobs/4/release/`.
2. Confirm registration `UAT 404D`.
3. Enter:
   - Final mileage: `40400`
   - Final vehicle condition:
     `Vehicle clean and ready for customer collection.`
   - Received by: `UAT Paid Customer`
   - Receiver contact: `+256700000404`
   - Handover notes:
     `Keys and service documents handed over.`
4. Submit.

Expected:

- Release succeeds without an override.
- Job status becomes `RELEASED`.
- A vehicle-release record is created.

Evidence: release-detail screenshot.

Result: __________

### UAT-REC-05 — Billing is forbidden

1. Open `http://127.0.0.1:8000/billing/`.

Expected:

- Access Denied page or HTTP `403`.
- No invoice data is displayed.

Evidence: access-denied screenshot.

Result: __________

### UAT-REC-06 — Stock reservation is forbidden

1. Open `/inventory/requirements/1/reserve/`.

Expected:

- Access Denied page or HTTP `403`.
- No stock reservation is created.

Evidence: access-denied screenshot.

Result: __________

## Verified execution results

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-REC-01 | PASS | `evidence/receptionist/UAT-REC-01-customer-created.png` |  | Customer was created with a generated customer number. |
| UAT-REC-02 | PASS | `evidence/receptionist/UAT-REC-02-vehicle-created.png` |  | UAT 606F was registered to the new customer. |
| UAT-REC-03 | PASS | `evidence/receptionist/UAT-REC-03-job-card-created.png` |  | An OPEN job card was created for UAT 606F. |
| UAT-REC-04 | PASS | `evidence/receptionist/UAT-REC-04-paid-release.png` |  | Fully paid UAT 404D was released without a payment override. |
| UAT-REC-05 | PASS | `evidence/receptionist/UAT-REC-05-billing-denied.png` |  | Receptionist billing access correctly returned HTTP 403. |
| UAT-REC-06 | PASS | `evidence/receptionist/UAT-REC-06-stock-reservation-denied.png` |  | Receptionist stock-reservation access correctly returned HTTP 403. |

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
