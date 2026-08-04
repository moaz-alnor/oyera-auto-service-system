# OYERA Release-Candidate Smoke-Test Matrix

- Validation date: 2026-08-04
- Environment: Local release-candidate development database
- Django settings: `config.settings.development`
- Audit host: `localhost`
- Test type: Read-only authenticated navigation and permission audit

## Acceptance criteria

The release candidate passes when:

1. All six role accounts authenticate successfully.
2. Every authenticated dashboard returns HTTP `200`.
3. Permitted scenario pages return `2xx` or an expected redirect.
4. Forbidden role actions return HTTP `403`.
5. No tested route returns `400`, `404`, or `5xx`.
6. The audit process exits with status zero.

## Result

**PASS**

The detailed role-by-role evidence follows.

---

# OYERA Release-Candidate Role Navigation Audit

- Audit host: `localhost`

| Role | Login | Dashboard | Links | 2xx | 3xx | 403 | 400 | 404 | Other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Administrator | PASS | 200 | 24 | 24 | 0 | 0 | 0 | 0 | 0 |
| Manager | PASS | 200 | 23 | 24 | 0 | 0 | 0 | 0 | 0 |
| Receptionist | PASS | 200 | 18 | 12 | 0 | 12 | 0 | 0 | 0 |
| Senior Technician | PASS | 200 | 15 | 13 | 0 | 11 | 0 | 0 | 0 |
| Technician | PASS | 200 | 9 | 1 | 0 | 23 | 0 | 0 | 0 |
| Cashier | PASS | 200 | 21 | 16 | 0 | 8 | 0 | 0 | 0 |

## Administrator

- Username: `admin`
- Login: PASS
- Dashboard: `200`

### Visible internal links

- `/`
- `/admin/`
- `/billing/`
- `/customers/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/jobs/4/`
- `/jobs/4/release/`
- `/jobs/5/`
- `/jobs/5/release/`
- `/products/`
- `/purchasing/purchase-orders/2/`
- `/purchasing/purchase-orders/?status=SUBMITTED`
- `/purchasing/supplier-invoices/`
- `/purchasing/supplier-invoices/2/`
- `/purchasing/supplier-invoices/3/`
- `/purchasing/supplier-invoices/?overdue=on`
- `/purchasing/suppliers/`
- `/quotations/`
- `/reports/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Seeded scenario responses

| Status | Classification | Path | Redirect destination |
|---:|---|---|---|
| 200 | SUCCESS | `/purchasing/purchase-orders/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/2/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/receipts/new/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/4/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/5/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/2/` | `` |
| 200 | SUCCESS | `/inventory/requirements/1/reserve/` | `` |
| 200 | SUCCESS | `/inventory/reservations/1/issue/` | `` |
| 200 | SUCCESS | `/inventory/movements/4/return/` | `` |
| 200 | SUCCESS | `/inventory/1/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/new/?purchase_order=5` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/1/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/2/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/3/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-payments/1/void/` | `` |
| 200 | SUCCESS | `/jobs/4/release/` | `` |
| 200 | SUCCESS | `/jobs/5/release/` | `` |
| 200 | SUCCESS | `/billing/1/` | `` |
| 200 | SUCCESS | `/billing/2/` | `` |

## Manager

- Username: `manager`
- Login: PASS
- Dashboard: `200`

### Visible internal links

- `/`
- `/billing/`
- `/customers/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/jobs/4/`
- `/jobs/4/release/`
- `/jobs/5/`
- `/jobs/5/release/`
- `/products/`
- `/purchasing/purchase-orders/2/`
- `/purchasing/purchase-orders/?status=SUBMITTED`
- `/purchasing/supplier-invoices/`
- `/purchasing/supplier-invoices/2/`
- `/purchasing/supplier-invoices/3/`
- `/purchasing/supplier-invoices/?overdue=on`
- `/purchasing/suppliers/`
- `/quotations/`
- `/reports/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Seeded scenario responses

| Status | Classification | Path | Redirect destination |
|---:|---|---|---|
| 200 | SUCCESS | `/purchasing/purchase-orders/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/2/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/receipts/new/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/4/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/5/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/2/` | `` |
| 200 | SUCCESS | `/inventory/requirements/1/reserve/` | `` |
| 200 | SUCCESS | `/inventory/reservations/1/issue/` | `` |
| 200 | SUCCESS | `/inventory/movements/4/return/` | `` |
| 200 | SUCCESS | `/inventory/1/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/new/?purchase_order=5` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/1/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/2/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/3/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-payments/1/void/` | `` |
| 200 | SUCCESS | `/jobs/4/release/` | `` |
| 200 | SUCCESS | `/jobs/5/release/` | `` |
| 200 | SUCCESS | `/billing/1/` | `` |
| 200 | SUCCESS | `/billing/2/` | `` |

## Receptionist

- Username: `receptionist`
- Login: PASS
- Dashboard: `200`

### Visible internal links

- `/`
- `/customers/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/jobs/4/`
- `/jobs/4/release/`
- `/jobs/5/`
- `/jobs/5/release/`
- `/products/`
- `/purchasing/purchase-orders/2/`
- `/purchasing/purchase-orders/?status=SUBMITTED`
- `/purchasing/suppliers/`
- `/quotations/`
- `/reports/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Seeded scenario responses

| Status | Classification | Path | Redirect destination |
|---:|---|---|---|
| 200 | SUCCESS | `/purchasing/purchase-orders/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/2/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/3/receipts/new/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/4/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/5/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/2/` | `` |
| 403 | FORBIDDEN | `/inventory/requirements/1/reserve/` | `` |
| 403 | FORBIDDEN | `/inventory/reservations/1/issue/` | `` |
| 403 | FORBIDDEN | `/inventory/movements/4/return/` | `` |
| 200 | SUCCESS | `/inventory/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/new/?purchase_order=5` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/2/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-payments/1/void/` | `` |
| 200 | SUCCESS | `/jobs/4/release/` | `` |
| 200 | SUCCESS | `/jobs/5/release/` | `` |
| 403 | FORBIDDEN | `/billing/1/` | `` |
| 403 | FORBIDDEN | `/billing/2/` | `` |

## Senior Technician

- Username: `senior_technician`
- Login: PASS
- Dashboard: `200`

### Visible internal links

- `/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/jobs/4/`
- `/jobs/5/`
- `/products/`
- `/purchasing/purchase-orders/2/`
- `/purchasing/purchase-orders/?status=SUBMITTED`
- `/purchasing/suppliers/`
- `/quotations/`
- `/reports/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Seeded scenario responses

| Status | Classification | Path | Redirect destination |
|---:|---|---|---|
| 200 | SUCCESS | `/purchasing/purchase-orders/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/2/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/3/receipts/new/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/4/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/5/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/2/` | `` |
| 200 | SUCCESS | `/inventory/requirements/1/reserve/` | `` |
| 200 | SUCCESS | `/inventory/reservations/1/issue/` | `` |
| 200 | SUCCESS | `/inventory/movements/4/return/` | `` |
| 200 | SUCCESS | `/inventory/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/new/?purchase_order=5` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/2/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-payments/1/void/` | `` |
| 403 | FORBIDDEN | `/jobs/4/release/` | `` |
| 403 | FORBIDDEN | `/jobs/5/release/` | `` |
| 403 | FORBIDDEN | `/billing/1/` | `` |
| 403 | FORBIDDEN | `/billing/2/` | `` |

## Technician

- Username: `technician`
- Login: PASS
- Dashboard: `200`

### Visible internal links

- `/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/products/`
- `/quotations/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Seeded scenario responses

| Status | Classification | Path | Redirect destination |
|---:|---|---|---|
| 403 | FORBIDDEN | `/purchasing/purchase-orders/` | `` |
| 403 | FORBIDDEN | `/purchasing/goods-receipts/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/2/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/3/receipts/new/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/4/` | `` |
| 403 | FORBIDDEN | `/purchasing/goods-receipts/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/5/` | `` |
| 403 | FORBIDDEN | `/purchasing/goods-receipts/2/` | `` |
| 403 | FORBIDDEN | `/inventory/requirements/1/reserve/` | `` |
| 403 | FORBIDDEN | `/inventory/reservations/1/issue/` | `` |
| 403 | FORBIDDEN | `/inventory/movements/4/return/` | `` |
| 200 | SUCCESS | `/inventory/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/new/?purchase_order=5` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/1/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/2/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-payments/1/void/` | `` |
| 403 | FORBIDDEN | `/jobs/4/release/` | `` |
| 403 | FORBIDDEN | `/jobs/5/release/` | `` |
| 403 | FORBIDDEN | `/billing/1/` | `` |
| 403 | FORBIDDEN | `/billing/2/` | `` |

## Cashier

- Username: `cashier`
- Login: PASS
- Dashboard: `200`

### Visible internal links

- `/`
- `/billing/`
- `/customers/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/jobs/4/`
- `/jobs/5/`
- `/products/`
- `/purchasing/purchase-orders/2/`
- `/purchasing/purchase-orders/?status=SUBMITTED`
- `/purchasing/supplier-invoices/`
- `/purchasing/supplier-invoices/2/`
- `/purchasing/supplier-invoices/3/`
- `/purchasing/supplier-invoices/?overdue=on`
- `/purchasing/suppliers/`
- `/quotations/`
- `/reports/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Seeded scenario responses

| Status | Classification | Path | Redirect destination |
|---:|---|---|---|
| 200 | SUCCESS | `/purchasing/purchase-orders/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/2/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/purchase-orders/3/receipts/new/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/4/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/1/` | `` |
| 200 | SUCCESS | `/purchasing/purchase-orders/5/` | `` |
| 200 | SUCCESS | `/purchasing/goods-receipts/2/` | `` |
| 403 | FORBIDDEN | `/inventory/requirements/1/reserve/` | `` |
| 403 | FORBIDDEN | `/inventory/reservations/1/issue/` | `` |
| 403 | FORBIDDEN | `/inventory/movements/4/return/` | `` |
| 200 | SUCCESS | `/inventory/1/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-invoices/new/?purchase_order=5` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/1/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/2/` | `` |
| 200 | SUCCESS | `/purchasing/supplier-invoices/3/` | `` |
| 403 | FORBIDDEN | `/purchasing/supplier-payments/1/void/` | `` |
| 403 | FORBIDDEN | `/jobs/4/release/` | `` |
| 403 | FORBIDDEN | `/jobs/5/release/` | `` |
| 200 | SUCCESS | `/billing/1/` | `` |
| 200 | SUCCESS | `/billing/2/` | `` |

## Automated result

**PASS — all six accounts logged in, all dashboards returned 200, and every scenario returned an expected response.**
