# OYERA UAT Execution Results

- Execution date: 2026-08-04
- Environment: Local development UAT database
- Casebook: `docs/uat/role-uat-casebook.md`
- Status values: PASS, FAIL, BLOCKED, NOT RUN

## Administrator

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-ADM-01 | PASS | `evidence/administrator/UAT-ADM-01-dashboard.png` |  | Automated Chrome login and dashboard navigation verification passed. |
| UAT-ADM-02 | PASS | `evidence/administrator/UAT-ADM-02-django-admin.png` |  | Django staff and superuser access passed. |
| UAT-ADM-03 | PASS | `evidence/administrator/` and `evidence/csv/` |  | Four report pages and four authenticated CSV exports passed. |
| UAT-ADM-04 | PASS | `evidence/administrator/UAT-ADM-04-purchase-order-approved.png` |  | DEMO-PO-SUBMITTED changed to APPROVED with administrator audit evidence. |

## Manager

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-MGR-01 | PASS | `evidence/manager/UAT-MGR-01-dashboard.png` |  | Automated Manager login and dashboard verification passed. |
| UAT-MGR-02 | PASS | `evidence/manager/` and `evidence/csv/` |  | Four Manager report pages and four CSV exports passed. |
| UAT-MGR-03 | PASS | `evidence/manager/UAT-MGR-03-purchase-order-approved.png` |  | DEMO-PO-SUBMITTED was approved by manager. |
| UAT-MGR-04 | PASS | `evidence/manager/UAT-MGR-04-unpaid-release-approved.png` |  | UAT 505E was released with a Manager payment override and outstanding balance. |
| UAT-MGR-05 | PASS | `evidence/manager/UAT-MGR-05-admin-denied.png` |  | Manager was redirected to the Django admin login page. |

## Receptionist

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-REC-01 | PASS | `evidence/receptionist/UAT-REC-01-customer-created.png` |  | Customer was created with a generated customer number. |
| UAT-REC-02 | PASS | `evidence/receptionist/UAT-REC-02-vehicle-created.png` |  | UAT 606F was registered to the new customer. |
| UAT-REC-03 | PASS | `evidence/receptionist/UAT-REC-03-job-card-created.png` |  | An OPEN job card was created for UAT 606F. |
| UAT-REC-04 | PASS | `evidence/receptionist/UAT-REC-04-paid-release.png` |  | Fully paid UAT 404D was released without a payment override. |
| UAT-REC-05 | PASS | `evidence/receptionist/UAT-REC-05-billing-denied.png` |  | Receptionist billing access correctly returned HTTP 403. |
| UAT-REC-06 | PASS | `evidence/receptionist/UAT-REC-06-stock-reservation-denied.png` |  | Receptionist stock-reservation access correctly returned HTTP 403. |

## Senior Technician

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-SEN-01 | PASS | `evidence/senior-technician/UAT-SEN-01-stock-reserved.png` |  | UAT 101A stock was reserved by senior_technician. |
| UAT-SEN-02 | PASS | `evidence/senior-technician/UAT-SEN-02-stock-issued.png` |  | UAT 202B reservation became PARTIALLY_ISSUED. |
| UAT-SEN-03 | PASS | `evidence/senior-technician/UAT-SEN-03-stock-returned.png` |  | A 0.500 stock return was recorded for UAT 303C. |
| UAT-SEN-04 | PASS | `evidence/senior-technician/UAT-SEN-04a-work-order-started.png`, `UAT-SEN-04b-work-order-held.png`, and `UAT-SEN-04c-work-order-resumed.png` |  | UAT 202B completed the start, hold, and resume cycle. |
| UAT-SEN-05 | PASS | `evidence/senior-technician/UAT-SEN-05-technical-note-added.png` |  | An append-only TECHNICAL task note was recorded. |
| UAT-SEN-06 | PASS | `evidence/senior-technician/UAT-SEN-06-billing-denied.png` |  | Senior Technician billing access correctly returned HTTP 403. |

## Technician

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-TEC-01 | PASS | `evidence/technician/UAT-TEC-01-dashboard.png` |  | Technician login and assigned-work navigation passed. |
| UAT-TEC-02 | PASS | `evidence/technician/UAT-TEC-02-task-blocked.png` |  | Assigned UAT 202B task was started and blocked with an auditable reason. |
| UAT-TEC-03 | PASS | `evidence/technician/UAT-TEC-03-task-awaiting-review.png` |  | Assigned UAT 303C task was submitted with completion evidence. |
| UAT-TEC-04 | PASS | `evidence/technician/UAT-TEC-04-approval-rejected.png` |  | Technician self-approval was rejected; the task remained AWAITING_REVIEW. |
| UAT-TEC-05 | PASS | `evidence/technician/UAT-TEC-05-reports-denied.png` |  | Technician reports access correctly returned HTTP 403. |

## Cashier

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-CAS-01 | PASS | `evidence/cashier/` and `evidence/csv/` |  | Customer-finance and purchasing reports and CSV exports passed. |
| UAT-CAS-02 | PASS | `evidence/cashier/UAT-CAS-02-customer-payment.png` |  | A UGX 10000.00 customer payment was recorded by cashier. |
| UAT-CAS-03 | PASS | `evidence/cashier/UAT-CAS-03-supplier-payment.png` |  | A UGX 25000.00 supplier payment was recorded by cashier. |
| UAT-CAS-04 | PASS | `evidence/cashier/UAT-CAS-04-workshop-report-denied.png` |  | Cashier workshop-report access correctly returned HTTP 403. |
| UAT-CAS-05 | PASS | `evidence/cashier/UAT-CAS-05-inventory-report-denied.png` |  | Cashier inventory-report access correctly returned HTTP 403. |
| UAT-CAS-06 | PASS | `evidence/cashier/UAT-CAS-06-vehicle-release-denied.png` |  | Cashier vehicle-release access correctly returned HTTP 403. |

## Final acceptance

| Responsibility | Name | Signature | Date |
| --- | --- | --- | --- |
| Tester |  |  |  |
| Business representative |  |  |  |
| System owner |  |  |  |
| Developer |  |  |  |
