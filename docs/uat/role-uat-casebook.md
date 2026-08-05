# OYERA Role-by-Role User Acceptance Test Casebook

- Generated: 2026-08-04
- Base URL: `http://127.0.0.1:8000`
- Database baseline: `python src/manage.py reset_demo_data --yes`
- Result fields: PASS, FAIL, or BLOCKED

## Purpose

This casebook gives the tester exact accounts, paths, input values,
expected results, forbidden results, reset steps, and evidence requirements.

## Global preparation

1. Keep the backup created before UAT.
2. Run:

       python src/manage.py reset_demo_data --yes

3. Start OYERA:

       python src/manage.py runserver 127.0.0.1:8000

4. Open `http://127.0.0.1:8000`.
5. Use a private browser window or log out between roles.
6. Reset the demo database before beginning each role section.
7. Stop immediately and record a defect if an expected result differs.

## Evidence naming

Use:

`UAT-<ROLE>-<CASE>-<short-description>.png`

Capture:

- the browser URL,
- the completed form or resulting record,
- any success or error message,
- the final status,
- downloaded CSV files where required.

## Exact demonstration accounts

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `AdminDemo123!` |
| Manager | `manager` | `ManagerDemo123!` |
| Receptionist | `receptionist` | `ReceptionDemo123!` |
| Senior Technician | `senior_technician` | `SeniorTechDemo123!` |
| Technician | `technician` | `TechnicianDemo123!` |
| Cashier | `cashier` | `CashierDemo123!` |

## Resolved seeded scenarios

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

# Administrator UAT

Reset the database, then log in as `admin`.

## UAT-ADM-01 — Authentication and dashboard

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

## UAT-ADM-02 — Django administration

1. Open `http://127.0.0.1:8000/admin/`.

Expected:

- Django administration index opens.
- The account is recognised as staff and superuser.
- No permission-denied page appears.

Evidence: administration index screenshot.

Result: __________

## UAT-ADM-03 — Complete operational reporting

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

## UAT-ADM-04 — Approve submitted purchase order

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

# Manager UAT

Reset the database, then log in as `manager`.

## UAT-MGR-01 — Authentication and dashboard

Expected:

- Login succeeds.
- Operational modules and reports are visible.
- Django administration is not available as a normal Manager function.

Evidence: dashboard screenshot.

Result: __________

## UAT-MGR-02 — Reports and CSV exports

Repeat all report and export URLs from UAT-ADM-03.

Expected:

- All report pages and CSV exports succeed.

Evidence: one screenshot per report and exported files.

Result: __________

## UAT-MGR-03 — Approve purchase order

1. Open `/purchasing/purchase-orders/2/approve/`.
2. Confirm `DEMO-PO-SUBMITTED`.
3. Tick the approval confirmation.
4. Submit.

Expected:

- Status becomes `APPROVED`.

Evidence: final status screenshot.

Result: __________

## UAT-MGR-04 — Authorise unpaid vehicle release

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

## UAT-MGR-05 — Manager cannot enter Django administration

1. Open `http://127.0.0.1:8000/admin/`.

Expected:

- The Django administration index does not open.
- The user is redirected to the admin login page because the Manager
  is not a staff administrator.

Evidence: redirected URL screenshot.

Result: __________

# Receptionist UAT

Reset the database, then log in as `receptionist`.

## UAT-REC-01 — Register customer

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

## UAT-REC-02 — Register vehicle

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

## UAT-REC-03 — Open job card

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

## UAT-REC-04 — Release fully paid vehicle

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

## UAT-REC-05 — Billing is forbidden

1. Open `http://127.0.0.1:8000/billing/`.

Expected:

- Access Denied page or HTTP `403`.
- No invoice data is displayed.

Evidence: access-denied screenshot.

Result: __________

## UAT-REC-06 — Stock reservation is forbidden

1. Open `/inventory/requirements/1/reserve/`.

Expected:

- Access Denied page or HTTP `403`.
- No stock reservation is created.

Evidence: access-denied screenshot.

Result: __________

# Senior Technician UAT

Reset the database, then log in as `senior_technician`.

## UAT-SEN-01 — Reserve required stock

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

## UAT-SEN-02 — Issue reserved stock

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

## UAT-SEN-03 — Return issued stock

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

## UAT-SEN-04 — Start, hold, and resume work order

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

## UAT-SEN-05 — Add workshop note

1. Open `/workshop/tasks/2/notes/new/`.
2. Select note type `Technical`.
3. Enter:
   `Senior Technician verified the assigned UAT task.`
4. Save.

Expected:

- Append-only task note is visible with author and timestamp.

Evidence: task-note screenshot.

Result: __________

## UAT-SEN-06 — Billing is forbidden

1. Open `http://127.0.0.1:8000/billing/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

# Technician UAT

Reset the database.

## Technician preparation by Administrator

Before logging in as Technician:

1. Log in as `admin`.
2. Open `/workshop/2/start/` and start the order.
3. Open `/workshop/3/start/` and start the order.
4. Log out.
5. Log in as `technician`.

## UAT-TEC-01 — Assigned-work visibility

Expected:

- Login succeeds.
- Workshop, jobs, quotations, products, services, vehicles, and
  read-only inventory links are visible.
- Billing, purchasing finance, and reports are not visible.

Evidence: Technician dashboard screenshot.

Result: __________

## UAT-TEC-02 — Start and block assigned task

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

## UAT-TEC-03 — Complete work and submit for review

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

## UAT-TEC-04 — Task approval is forbidden

1. Open `/workshop/tasks/3/approve/`.

Expected:

- Access Denied page or HTTP `403`.
- Task remains `AWAITING_REVIEW`.

Evidence: access-denied and unchanged-status screenshots.

Result: __________

## UAT-TEC-05 — Reports are forbidden

1. Open `/reports/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

# Cashier UAT

Reset the database, then log in as `cashier`.

## UAT-CAS-01 — Finance reporting

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

## UAT-CAS-02 — Record customer payment

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

## UAT-CAS-03 — Record supplier payment

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

## UAT-CAS-04 — Workshop report is forbidden

1. Open `/reports/workshop-operations/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

## UAT-CAS-05 — Inventory report is forbidden

1. Open `/reports/inventory-activity/`.

Expected:

- Access Denied page or HTTP `403`.

Evidence: access-denied screenshot.

Result: __________

## UAT-CAS-06 — Vehicle release is forbidden

1. Open `/jobs/4/release/`.

Expected:

- Access Denied page or HTTP `403`.
- No vehicle-release record is created.

Evidence: access-denied screenshot.

Result: __________

# Final UAT acceptance

The UAT cycle passes only when:

- all allowed cases succeed,
- all forbidden cases return access denial,
- no unexpected `400`, `404`, or `500` response occurs,
- all evidence files are captured,
- every failed case has an issue reference,
- the database can be reset to the original demonstration baseline.

## Acceptance signatures

| Responsibility | Name | Signature | Date |
| --- | --- | --- | --- |
| Tester |  |  |  |
| Business representative |  |  |  |
| System owner |  |  |  |
| Developer |  |  |  |
