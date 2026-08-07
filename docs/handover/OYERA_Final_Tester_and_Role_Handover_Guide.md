# OYERA Final Tester and Role Handover Guide

[TOC]

## Document control

| Field | Value |
| --- | --- |
| System | OYERA Auto Service System |
| Document | Final Tester and Role Handover Guide |
| Generated | 2026-08-05 |
| Branch | `feature/uat-handover` |
| Source commit | `61985a3` |
| UAT result | **32/32 PASS** |
| Automated tests | **826 PASS** |
| Evidence | 41 screenshots and 10 CSV files |

## Purpose and use

This is the authoritative handover guide for testing, demonstrating,
operating, deploying, and accepting OYERA.

The tester should not infer missing values or invent test data. Each role
section provides the account, exact path, values to enter, expected result,
forbidden result, and required evidence.

## Demonstration-data warning

The listed usernames and passwords are for local demonstration and UAT only.
They are intentionally predictable so that the acceptance suite can be
repeated. They are not production credentials.

## Verified release status

## OYERA Release Validation Record

| Item | Verified result |
| --- | ---: |
| Role-based UAT cases | 32 / 32 PASS |
| Evidence screenshots | 41 |
| CSV evidence exports | 10 |
| Automated project tests | 826 PASS |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Ruff linting | PASS |
| Ruff formatting | PASS |
| Shell-script syntax checks | PASS |
| Release branch | `feature/uat-handover` |
| UAT source commit | `61985a3` |

> The role automation resets the local demonstration database before
> each role. The final local database reflects the last executed role,
> while all verified role outcomes remain preserved in the execution
> ledger and evidence directories.

### Security note

All credentials in these guides are demonstration credentials created by
`reset_demo_data`. They must never be reused for a production deployment.
Production users must receive unique accounts and independently generated
passwords.


## Exact UAT baseline

## OYERA UAT Baseline

This document records the exact database, roles, credentials,
permissions, and dashboard links used to begin UAT.

### Demo accounts

| Role | Username | Password | Login | Dashboard |
| --- | --- | --- | ---: | ---: |
| Administrator | `admin` | `AdminDemo123!` | PASS | 200 |
| Manager | `manager` | `ManagerDemo123!` | PASS | 200 |
| Receptionist | `receptionist` | `ReceptionDemo123!` | PASS | 200 |
| Senior Technician | `senior_technician` | `SeniorTechDemo123!` | PASS | 200 |
| Technician | `technician` | `TechnicianDemo123!` | PASS | 200 |
| Cashier | `cashier` | `CashierDemo123!` | PASS | 200 |

### Seeded business records

| Model | Count | Note |
| --- | ---: | --- |
| `accounts.User` | 6 | Seeded records |
| `billing.Invoice` | 2 | Seeded records |
| `billing.InvoiceProductLine` | 0 | Seeded records |
| `billing.InvoiceServiceLine` | 2 | Seeded records |
| `billing.Payment` | 1 | Seeded records |
| `customers.Customer` | 1 | Seeded records |
| `inventory.InventoryItem` | 1 | Seeded records |
| `inventory.StockLocation` | 1 | Seeded records |
| `inventory.StockMovement` | 4 | Seeded records |
| `inventory.StockReservation` | 2 | Seeded records |
| `jobs.Inspection` | 0 | Seeded records |
| `jobs.JobCard` | 5 | Seeded records |
| `jobs.JobNote` | 0 | Seeded records |
| `jobs.VehicleRelease` | 0 | Seeded records |
| `product_catalogue.Product` | 1 | Seeded records |
| `product_catalogue.ProductCategory` | 1 | Seeded records |
| `product_catalogue.ProductPrice` | 1 | Seeded records |
| `purchasing.GoodsReceipt` | 2 | Seeded records |
| `purchasing.GoodsReceiptLine` | 2 | Seeded records |
| `purchasing.PurchaseOrder` | 5 | Seeded records |
| `purchasing.PurchaseOrderLine` | 5 | Seeded records |
| `purchasing.Supplier` | 1 | Seeded records |
| `purchasing.SupplierInvoice` | 3 | Seeded records |
| `purchasing.SupplierInvoiceLine` | 3 | Seeded records |
| `purchasing.SupplierPayment` | 1 | Seeded records |
| `quotations.Quotation` | 5 | Seeded records |
| `quotations.QuotationProductLine` | 5 | Seeded records |
| `quotations.QuotationServiceLine` | 5 | Seeded records |
| `reports.ReportAccess` | Not applicable | Unmanaged permission model |
| `service_catalogue.Service` | 1 | Seeded records |
| `service_catalogue.ServiceApplicability` | 1 | Seeded records |
| `service_catalogue.ServicePrice` | 1 | Seeded records |
| `vehicles.Vehicle` | 5 | Seeded records |
| `vehicles.VehicleOwnership` | 5 | Seeded records |
| `workshop.TechnicianAssignment` | 4 | Seeded records |
| `workshop.WorkOrder` | 5 | Seeded records |
| `workshop.WorkProductRequirement` | 5 | Seeded records |
| `workshop.WorkTask` | 5 | Seeded records |
| `workshop.WorkTaskNote` | 0 | Seeded records |

### Administrator

- Username: `admin`
- Password: `AdminDemo123!`
- Assigned group: `Administrator`
- Effective permissions: 224
- Visible dashboard links: 24

#### Effective permissions

- `accounts.add_user`
- `accounts.change_user`
- `accounts.delete_user`
- `accounts.view_user`
- `admin.add_logentry`
- `admin.change_logentry`
- `admin.delete_logentry`
- `admin.view_logentry`
- `auth.add_group`
- `auth.add_permission`
- `auth.change_group`
- `auth.change_permission`
- `auth.delete_group`
- `auth.delete_permission`
- `auth.view_group`
- `auth.view_permission`
- `billing.add_invoice`
- `billing.add_invoiceproductline`
- `billing.add_invoiceserviceline`
- `billing.add_payment`
- `billing.change_invoice`
- `billing.change_invoiceproductline`
- `billing.change_invoiceserviceline`
- `billing.change_payment`
- `billing.delete_invoice`
- `billing.delete_invoiceproductline`
- `billing.delete_invoiceserviceline`
- `billing.delete_payment`
- `billing.issue_invoice`
- `billing.record_payment`
- `billing.view_invoice`
- `billing.view_invoiceproductline`
- `billing.view_invoiceserviceline`
- `billing.view_payment`
- `billing.void_invoice`
- `billing.void_payment`
- `contenttypes.add_contenttype`
- `contenttypes.change_contenttype`
- `contenttypes.delete_contenttype`
- `contenttypes.view_contenttype`
- `customers.add_customer`
- `customers.change_customer`
- `customers.deactivate_customer`
- `customers.delete_customer`
- `customers.reactivate_customer`
- `customers.view_customer`
- `inventory.add_inventoryitem`
- `inventory.add_stocklocation`
- `inventory.add_stockmovement`
- `inventory.add_stockreservation`
- `inventory.adjust_stock`
- `inventory.change_inventoryitem`
- `inventory.change_stocklocation`
- `inventory.change_stockmovement`
- `inventory.change_stockreservation`
- `inventory.delete_inventoryitem`
- `inventory.delete_stocklocation`
- `inventory.delete_stockmovement`
- `inventory.delete_stockreservation`
- `inventory.issue_stock`
- `inventory.receive_stock`
- `inventory.release_stock_reservation`
- `inventory.reserve_stock`
- `inventory.return_stock`
- `inventory.view_inventoryitem`
- `inventory.view_stocklocation`
- `inventory.view_stockmovement`
- `inventory.view_stockreservation`
- `jobs.add_inspection`
- `jobs.add_jobcard`
- `jobs.add_jobnote`
- `jobs.add_vehiclerelease`
- `jobs.cancel_jobcard`
- `jobs.change_inspection`
- `jobs.change_jobcard`
- `jobs.change_jobnote`
- `jobs.change_vehiclerelease`
- `jobs.delete_inspection`
- `jobs.delete_jobcard`
- `jobs.delete_jobnote`
- `jobs.delete_vehiclerelease`
- `jobs.override_vehicle_release_payment`
- `jobs.release_vehicle`
- `jobs.view_inspection`
- `jobs.view_jobcard`
- `jobs.view_jobnote`
- `jobs.view_vehiclerelease`
- `product_catalogue.add_product`
- `product_catalogue.add_productcategory`
- `product_catalogue.add_productprice`
- `product_catalogue.change_product`
- `product_catalogue.change_product_price`
- `product_catalogue.change_productcategory`
- `product_catalogue.change_productprice`
- `product_catalogue.deactivate_product`
- `product_catalogue.delete_product`
- `product_catalogue.delete_productcategory`
- `product_catalogue.delete_productprice`
- `product_catalogue.reactivate_product`
- `product_catalogue.view_product`
- `product_catalogue.view_productcategory`
- `product_catalogue.view_productprice`
- `purchasing.add_goodsreceipt`
- `purchasing.add_goodsreceiptline`
- `purchasing.add_purchaseorder`
- `purchasing.add_purchaseorderline`
- `purchasing.add_supplier`
- `purchasing.add_supplierinvoice`
- `purchasing.add_supplierinvoiceline`
- `purchasing.add_supplierpayment`
- `purchasing.approve_purchase_order`
- `purchasing.cancel_purchase_order`
- `purchasing.change_goodsreceipt`
- `purchasing.change_goodsreceiptline`
- `purchasing.change_purchaseorder`
- `purchasing.change_purchaseorderline`
- `purchasing.change_supplier`
- `purchasing.change_supplierinvoice`
- `purchasing.change_supplierinvoiceline`
- `purchasing.change_supplierpayment`
- `purchasing.deactivate_supplier`
- `purchasing.delete_goodsreceipt`
- `purchasing.delete_goodsreceiptline`
- `purchasing.delete_purchaseorder`
- `purchasing.delete_purchaseorderline`
- `purchasing.delete_supplier`
- `purchasing.delete_supplierinvoice`
- `purchasing.delete_supplierinvoiceline`
- `purchasing.delete_supplierpayment`
- `purchasing.post_supplier_invoice`
- `purchasing.reactivate_supplier`
- `purchasing.receive_purchase_order`
- `purchasing.record_supplier_payment`
- `purchasing.submit_purchase_order`
- `purchasing.view_goodsreceipt`
- `purchasing.view_goodsreceiptline`
- `purchasing.view_purchaseorder`
- `purchasing.view_purchaseorderline`
- `purchasing.view_supplier`
- `purchasing.view_supplierinvoice`
- `purchasing.view_supplierinvoiceline`
- `purchasing.view_supplierpayment`
- `purchasing.void_supplier_invoice`
- `purchasing.void_supplier_payment`
- `quotations.add_quotation`
- `quotations.add_quotationproductline`
- `quotations.add_quotationserviceline`
- `quotations.approve_quotation`
- `quotations.change_quotation`
- `quotations.change_quotationproductline`
- `quotations.change_quotationserviceline`
- `quotations.delete_quotation`
- `quotations.delete_quotationproductline`
- `quotations.delete_quotationserviceline`
- `quotations.reject_quotation`
- `quotations.revise_quotation`
- `quotations.submit_quotation`
- `quotations.view_quotation`
- `quotations.view_quotationproductline`
- `quotations.view_quotationserviceline`
- `reports.access_reports`
- `reports.export_reports`
- `reports.view_customer_finance_report`
- `reports.view_inventory_report`
- `reports.view_purchasing_report`
- `reports.view_workshop_report`
- `service_catalogue.add_service`
- `service_catalogue.add_serviceapplicability`
- `service_catalogue.add_serviceprice`
- `service_catalogue.change_service`
- `service_catalogue.change_service_price`
- `service_catalogue.change_serviceapplicability`
- `service_catalogue.change_serviceprice`
- `service_catalogue.deactivate_service`
- `service_catalogue.delete_service`
- `service_catalogue.delete_serviceapplicability`
- `service_catalogue.delete_serviceprice`
- `service_catalogue.reactivate_service`
- `service_catalogue.view_service`
- `service_catalogue.view_serviceapplicability`
- `service_catalogue.view_serviceprice`
- `sessions.add_session`
- `sessions.change_session`
- `sessions.delete_session`
- `sessions.view_session`
- `vehicles.add_vehicle`
- `vehicles.add_vehicleownership`
- `vehicles.change_vehicle`
- `vehicles.change_vehicleownership`
- `vehicles.deactivate_vehicle`
- `vehicles.delete_vehicle`
- `vehicles.delete_vehicleownership`
- `vehicles.reactivate_vehicle`
- `vehicles.transfer_vehicle_owner`
- `vehicles.view_vehicle`
- `vehicles.view_vehicleownership`
- `workshop.add_technicianassignment`
- `workshop.add_workorder`
- `workshop.add_workproductrequirement`
- `workshop.add_worktask`
- `workshop.add_worktasknote`
- `workshop.assign_technician`
- `workshop.block_work_task`
- `workshop.change_technicianassignment`
- `workshop.change_workorder`
- `workshop.change_workproductrequirement`
- `workshop.change_worktask`
- `workshop.change_worktasknote`
- `workshop.complete_work_order`
- `workshop.complete_work_task`
- `workshop.delete_technicianassignment`
- `workshop.delete_workorder`
- `workshop.delete_workproductrequirement`
- `workshop.delete_worktask`
- `workshop.delete_worktasknote`
- `workshop.hold_work_order`
- `workshop.resume_work_order`
- `workshop.start_work_order`
- `workshop.start_work_task`
- `workshop.view_technicianassignment`
- `workshop.view_workorder`
- `workshop.view_workproductrequirement`
- `workshop.view_worktask`
- `workshop.view_worktasknote`

#### Visible dashboard links

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

### Manager

- Username: `manager`
- Password: `ManagerDemo123!`
- Assigned group: `Manager`
- Effective permissions: 102
- Visible dashboard links: 23

#### Effective permissions

- `billing.add_invoice`
- `billing.issue_invoice`
- `billing.record_payment`
- `billing.view_invoice`
- `billing.view_payment`
- `billing.void_invoice`
- `billing.void_payment`
- `customers.view_customer`
- `inventory.add_inventoryitem`
- `inventory.add_stocklocation`
- `inventory.adjust_stock`
- `inventory.change_inventoryitem`
- `inventory.change_stocklocation`
- `inventory.issue_stock`
- `inventory.receive_stock`
- `inventory.release_stock_reservation`
- `inventory.reserve_stock`
- `inventory.return_stock`
- `inventory.view_inventoryitem`
- `inventory.view_stocklocation`
- `inventory.view_stockmovement`
- `inventory.view_stockreservation`
- `jobs.add_inspection`
- `jobs.add_jobcard`
- `jobs.add_jobnote`
- `jobs.cancel_jobcard`
- `jobs.change_jobcard`
- `jobs.override_vehicle_release_payment`
- `jobs.release_vehicle`
- `jobs.view_inspection`
- `jobs.view_jobcard`
- `jobs.view_jobnote`
- `jobs.view_vehiclerelease`
- `product_catalogue.add_product`
- `product_catalogue.add_productcategory`
- `product_catalogue.change_product`
- `product_catalogue.change_product_price`
- `product_catalogue.change_productcategory`
- `product_catalogue.deactivate_product`
- `product_catalogue.reactivate_product`
- `product_catalogue.view_product`
- `product_catalogue.view_productcategory`
- `purchasing.add_purchaseorder`
- `purchasing.add_supplier`
- `purchasing.add_supplierinvoice`
- `purchasing.approve_purchase_order`
- `purchasing.cancel_purchase_order`
- `purchasing.change_purchaseorder`
- `purchasing.change_supplier`
- `purchasing.change_supplierinvoice`
- `purchasing.deactivate_supplier`
- `purchasing.post_supplier_invoice`
- `purchasing.reactivate_supplier`
- `purchasing.receive_purchase_order`
- `purchasing.record_supplier_payment`
- `purchasing.submit_purchase_order`
- `purchasing.view_goodsreceipt`
- `purchasing.view_purchaseorder`
- `purchasing.view_supplier`
- `purchasing.view_supplierinvoice`
- `purchasing.view_supplierpayment`
- `purchasing.void_supplier_invoice`
- `purchasing.void_supplier_payment`
- `quotations.add_quotation`
- `quotations.approve_quotation`
- `quotations.change_quotation`
- `quotations.reject_quotation`
- `quotations.revise_quotation`
- `quotations.submit_quotation`
- `quotations.view_quotation`
- `reports.access_reports`
- `reports.export_reports`
- `reports.view_customer_finance_report`
- `reports.view_inventory_report`
- `reports.view_purchasing_report`
- `reports.view_workshop_report`
- `service_catalogue.add_service`
- `service_catalogue.change_service`
- `service_catalogue.change_service_price`
- `service_catalogue.deactivate_service`
- `service_catalogue.reactivate_service`
- `service_catalogue.view_service`
- `vehicles.view_vehicle`
- `workshop.add_technicianassignment`
- `workshop.add_workorder`
- `workshop.add_worktasknote`
- `workshop.assign_technician`
- `workshop.block_work_task`
- `workshop.change_technicianassignment`
- `workshop.change_workorder`
- `workshop.change_worktask`
- `workshop.complete_work_order`
- `workshop.complete_work_task`
- `workshop.hold_work_order`
- `workshop.resume_work_order`
- `workshop.start_work_order`
- `workshop.start_work_task`
- `workshop.view_technicianassignment`
- `workshop.view_workorder`
- `workshop.view_workproductrequirement`
- `workshop.view_worktask`
- `workshop.view_worktasknote`

#### Visible dashboard links

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

### Receptionist

- Username: `receptionist`
- Password: `ReceptionDemo123!`
- Assigned group: `Receptionist`
- Effective permissions: 38
- Visible dashboard links: 18

#### Effective permissions

- `customers.add_customer`
- `customers.change_customer`
- `customers.view_customer`
- `inventory.view_inventoryitem`
- `inventory.view_stocklocation`
- `jobs.add_jobcard`
- `jobs.add_jobnote`
- `jobs.cancel_jobcard`
- `jobs.change_jobcard`
- `jobs.release_vehicle`
- `jobs.view_inspection`
- `jobs.view_jobcard`
- `jobs.view_jobnote`
- `jobs.view_vehiclerelease`
- `product_catalogue.view_product`
- `product_catalogue.view_productcategory`
- `purchasing.view_goodsreceipt`
- `purchasing.view_purchaseorder`
- `purchasing.view_supplier`
- `quotations.add_quotation`
- `quotations.approve_quotation`
- `quotations.change_quotation`
- `quotations.reject_quotation`
- `quotations.revise_quotation`
- `quotations.submit_quotation`
- `quotations.view_quotation`
- `reports.access_reports`
- `reports.view_workshop_report`
- `service_catalogue.view_service`
- `vehicles.add_vehicle`
- `vehicles.change_vehicle`
- `vehicles.transfer_vehicle_owner`
- `vehicles.view_vehicle`
- `workshop.view_technicianassignment`
- `workshop.view_workorder`
- `workshop.view_workproductrequirement`
- `workshop.view_worktask`
- `workshop.view_worktasknote`

#### Visible dashboard links

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

### Senior Technician

- Username: `senior_technician`
- Password: `SeniorTechDemo123!`
- Assigned group: `Senior Technician`
- Effective permissions: 41
- Visible dashboard links: 15

#### Effective permissions

- `inventory.issue_stock`
- `inventory.release_stock_reservation`
- `inventory.reserve_stock`
- `inventory.return_stock`
- `inventory.view_inventoryitem`
- `inventory.view_stocklocation`
- `inventory.view_stockmovement`
- `inventory.view_stockreservation`
- `jobs.add_inspection`
- `jobs.add_jobnote`
- `jobs.view_inspection`
- `jobs.view_jobcard`
- `jobs.view_jobnote`
- `jobs.view_vehiclerelease`
- `product_catalogue.view_product`
- `product_catalogue.view_productcategory`
- `purchasing.view_goodsreceipt`
- `purchasing.view_purchaseorder`
- `purchasing.view_supplier`
- `quotations.view_quotation`
- `reports.access_reports`
- `reports.view_workshop_report`
- `service_catalogue.view_service`
- `vehicles.view_vehicle`
- `workshop.add_technicianassignment`
- `workshop.add_worktasknote`
- `workshop.assign_technician`
- `workshop.block_work_task`
- `workshop.change_technicianassignment`
- `workshop.change_workorder`
- `workshop.change_worktask`
- `workshop.complete_work_task`
- `workshop.hold_work_order`
- `workshop.resume_work_order`
- `workshop.start_work_order`
- `workshop.start_work_task`
- `workshop.view_technicianassignment`
- `workshop.view_workorder`
- `workshop.view_workproductrequirement`
- `workshop.view_worktask`
- `workshop.view_worktasknote`

#### Visible dashboard links

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

### Technician

- Username: `technician`
- Password: `TechnicianDemo123!`
- Assigned group: `Technician`
- Effective permissions: 23
- Visible dashboard links: 9

#### Effective permissions

- `inventory.view_inventoryitem`
- `inventory.view_stocklocation`
- `inventory.view_stockreservation`
- `jobs.add_inspection`
- `jobs.add_jobnote`
- `jobs.view_inspection`
- `jobs.view_jobcard`
- `jobs.view_jobnote`
- `product_catalogue.view_product`
- `product_catalogue.view_productcategory`
- `quotations.view_quotation`
- `service_catalogue.view_service`
- `vehicles.view_vehicle`
- `workshop.add_worktasknote`
- `workshop.block_work_task`
- `workshop.change_worktask`
- `workshop.complete_work_task`
- `workshop.start_work_task`
- `workshop.view_technicianassignment`
- `workshop.view_workorder`
- `workshop.view_workproductrequirement`
- `workshop.view_worktask`
- `workshop.view_worktasknote`

#### Visible dashboard links

- `/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/products/`
- `/quotations/`
- `/services/`
- `/vehicles/`
- `/workshop/`

### Cashier

- Username: `cashier`
- Password: `CashierDemo123!`
- Assigned group: `Cashier`
- Effective permissions: 31
- Visible dashboard links: 21

#### Effective permissions

- `billing.add_invoice`
- `billing.issue_invoice`
- `billing.record_payment`
- `billing.view_invoice`
- `billing.view_payment`
- `customers.add_customer`
- `customers.change_customer`
- `customers.view_customer`
- `inventory.view_inventoryitem`
- `inventory.view_stocklocation`
- `jobs.view_inspection`
- `jobs.view_jobcard`
- `jobs.view_jobnote`
- `jobs.view_vehiclerelease`
- `product_catalogue.view_product`
- `product_catalogue.view_productcategory`
- `purchasing.record_supplier_payment`
- `purchasing.view_goodsreceipt`
- `purchasing.view_purchaseorder`
- `purchasing.view_supplier`
- `purchasing.view_supplierinvoice`
- `purchasing.view_supplierpayment`
- `quotations.view_quotation`
- `reports.access_reports`
- `reports.export_reports`
- `reports.view_customer_finance_report`
- `reports.view_purchasing_report`
- `service_catalogue.view_service`
- `vehicles.view_vehicle`
- `workshop.view_workorder`
- `workshop.view_workproductrequirement`

#### Visible dashboard links

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

### Baseline result

**PASS — all six accounts authenticated and all dashboards returned HTTP 200.**


## Complete role-by-role test casebook

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

## Final UAT acceptance

The UAT cycle passes only when:

- all allowed cases succeed,
- all forbidden cases return access denial,
- no unexpected `400`, `404`, or `500` response occurs,
- all evidence files are captured,
- every failed case has an issue reference,
- the database can be reset to the original demonstration baseline.

### Acceptance signatures

| Responsibility | Name | Signature | Date |
| --- | --- | --- | --- |
| Tester |  |  |  |
| Business representative |  |  |  |
| System owner |  |  |  |
| Developer |  |  |  |


## Verified UAT execution ledger

## OYERA UAT Execution Results

- Execution date: 2026-08-04
- Environment: Local development UAT database
- Casebook: `docs/uat/role-uat-casebook.md`
- Status values: PASS, FAIL, BLOCKED, NOT RUN

### Administrator

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-ADM-01 | PASS | `evidence/administrator/UAT-ADM-01-dashboard.png` |  | Automated Chrome login and dashboard navigation verification passed. |
| UAT-ADM-02 | PASS | `evidence/administrator/UAT-ADM-02-django-admin.png` |  | Django staff and superuser access passed. |
| UAT-ADM-03 | PASS | `evidence/administrator/` and `evidence/csv/` |  | Four report pages and four authenticated CSV exports passed. |
| UAT-ADM-04 | PASS | `evidence/administrator/UAT-ADM-04-purchase-order-approved.png` |  | DEMO-PO-SUBMITTED changed to APPROVED with administrator audit evidence. |

### Manager

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-MGR-01 | PASS | `evidence/manager/UAT-MGR-01-dashboard.png` |  | Automated Manager login and dashboard verification passed. |
| UAT-MGR-02 | PASS | `evidence/manager/` and `evidence/csv/` |  | Four Manager report pages and four CSV exports passed. |
| UAT-MGR-03 | PASS | `evidence/manager/UAT-MGR-03-purchase-order-approved.png` |  | DEMO-PO-SUBMITTED was approved by manager. |
| UAT-MGR-04 | PASS | `evidence/manager/UAT-MGR-04-unpaid-release-approved.png` |  | UAT 505E was released with a Manager payment override and outstanding balance. |
| UAT-MGR-05 | PASS | `evidence/manager/UAT-MGR-05-admin-denied.png` |  | Manager was redirected to the Django admin login page. |

### Receptionist

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-REC-01 | PASS | `evidence/receptionist/UAT-REC-01-customer-created.png` |  | Customer was created with a generated customer number. |
| UAT-REC-02 | PASS | `evidence/receptionist/UAT-REC-02-vehicle-created.png` |  | UAT 606F was registered to the new customer. |
| UAT-REC-03 | PASS | `evidence/receptionist/UAT-REC-03-job-card-created.png` |  | An OPEN job card was created for UAT 606F. |
| UAT-REC-04 | PASS | `evidence/receptionist/UAT-REC-04-paid-release.png` |  | Fully paid UAT 404D was released without a payment override. |
| UAT-REC-05 | PASS | `evidence/receptionist/UAT-REC-05-billing-denied.png` |  | Receptionist billing access correctly returned HTTP 403. |
| UAT-REC-06 | PASS | `evidence/receptionist/UAT-REC-06-stock-reservation-denied.png` |  | Receptionist stock-reservation access correctly returned HTTP 403. |

### Senior Technician

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-SEN-01 | PASS | `evidence/senior-technician/UAT-SEN-01-stock-reserved.png` |  | UAT 101A stock was reserved by senior_technician. |
| UAT-SEN-02 | PASS | `evidence/senior-technician/UAT-SEN-02-stock-issued.png` |  | UAT 202B reservation became PARTIALLY_ISSUED. |
| UAT-SEN-03 | PASS | `evidence/senior-technician/UAT-SEN-03-stock-returned.png` |  | A 0.500 stock return was recorded for UAT 303C. |
| UAT-SEN-04 | PASS | `evidence/senior-technician/UAT-SEN-04a-work-order-started.png`, `UAT-SEN-04b-work-order-held.png`, and `UAT-SEN-04c-work-order-resumed.png` |  | UAT 202B completed the start, hold, and resume cycle. |
| UAT-SEN-05 | PASS | `evidence/senior-technician/UAT-SEN-05-technical-note-added.png` |  | An append-only TECHNICAL task note was recorded. |
| UAT-SEN-06 | PASS | `evidence/senior-technician/UAT-SEN-06-billing-denied.png` |  | Senior Technician billing access correctly returned HTTP 403. |

### Technician

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-TEC-01 | PASS | `evidence/technician/UAT-TEC-01-dashboard.png` |  | Technician login and assigned-work navigation passed. |
| UAT-TEC-02 | PASS | `evidence/technician/UAT-TEC-02-task-blocked.png` |  | Assigned UAT 202B task was started and blocked with an auditable reason. |
| UAT-TEC-03 | PASS | `evidence/technician/UAT-TEC-03-task-awaiting-review.png` |  | Assigned UAT 303C task was submitted with completion evidence. |
| UAT-TEC-04 | PASS | `evidence/technician/UAT-TEC-04-approval-rejected.png` |  | Technician self-approval was rejected; the task remained AWAITING_REVIEW. |
| UAT-TEC-05 | PASS | `evidence/technician/UAT-TEC-05-reports-denied.png` |  | Technician reports access correctly returned HTTP 403. |

### Cashier

| Case | Status | Evidence | Issue | Notes |
| --- | --- | --- | --- | --- |
| UAT-CAS-01 | PASS | `evidence/cashier/` and `evidence/csv/` |  | Customer-finance and purchasing reports and CSV exports passed. |
| UAT-CAS-02 | PASS | `evidence/cashier/UAT-CAS-02-customer-payment.png` |  | A UGX 10000.00 customer payment was recorded by cashier. |
| UAT-CAS-03 | PASS | `evidence/cashier/UAT-CAS-03-supplier-payment.png` |  | A UGX 25000.00 supplier payment was recorded by cashier. |
| UAT-CAS-04 | PASS | `evidence/cashier/UAT-CAS-04-workshop-report-denied.png` |  | Cashier workshop-report access correctly returned HTTP 403. |
| UAT-CAS-05 | PASS | `evidence/cashier/UAT-CAS-05-inventory-report-denied.png` |  | Cashier inventory-report access correctly returned HTTP 403. |
| UAT-CAS-06 | PASS | `evidence/cashier/UAT-CAS-06-vehicle-release-denied.png` |  | Cashier vehicle-release access correctly returned HTTP 403. |

### Final acceptance

| Responsibility | Name | Signature | Date |
| --- | --- | --- | --- |
| Tester |  |  |  |
| Business representative |  |  |  |
| System owner |  |  |  |
| Developer |  |  |  |


## Database backup and restore guide

## OYERA Database Backup and Restore Guide

### Purpose

OYERA provides controlled PostgreSQL backup and restoration scripts:

- `scripts/db_backup.sh` creates and validates a backup archive.
- `scripts/db_restore.sh` restores an archive into a controlled target.

Backups may contain employee, customer, supplier, vehicle, financial,
inventory, purchasing, and workshop information. They must be treated as
confidential.

### Required tools

The workstation performing the operation requires:

- `pg_dump`
- `pg_restore`
- `psql`
- `createdb`
- `dropdb`

### Application database variables

The scripts use:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

The host defaults to `127.0.0.1`, and the port defaults to `5432`.

### Optional administrator connection

A production application role should not normally require permission to
create or delete databases. Database lifecycle operations can therefore use:

- `POSTGRES_ADMIN_HOST`
- `POSTGRES_ADMIN_PORT`
- `POSTGRES_ADMIN_USER`
- `POSTGRES_ADMIN_PASSWORD`

The administrator host and port default to the application database host and
port. The administrator user and password default to the application
credentials.

The administrator creates the target database and assigns ownership to
`POSTGRES_USER`. The archive itself is restored using the application role.

### Create a backup

Create a timestamped archive:

    scripts/db_backup.sh

Create an archive at a specific location:

    scripts/db_backup.sh /secure/location/oyera-production.dump

The backup script:

1. Uses PostgreSQL custom format.
2. Excludes ownership and privilege restoration.
3. Writes to a temporary partial file.
4. Validates the archive with `pg_restore --list`.
5. Applies file permission mode `600`.
6. Refuses to overwrite existing archives by default.

Intentional overwrite requires:

    OYERA_BACKUP_OVERWRITE=true

### Restore into a separate database

The normal verification method is:

    scripts/db_restore.sh \
      /secure/location/oyera-production.dump \
      oyera_restore_verification

The script validates the archive before creating or replacing a database.

### Existing-target protection

Replacing an existing database requires both:

    OYERA_RESTORE_REPLACE_EXISTING=true
    OYERA_RESTORE_CONFIRM_DATABASE=<exact target name>

### Configured-database protection

Restoring into the database named by `POSTGRES_DB` additionally requires:

    OYERA_ALLOW_PRODUCTION_RESTORE=true
    OYERA_PRODUCTION_RESTORE_CONFIRM=<exact target name>

All confirmation values must exactly match the selected target database.

### Verification requirements

After restoring into a separate database:

1. Compare public-table counts.
2. Compare Django migration counts.
3. Compare representative business-record counts.
4. Run Django system and migration checks.
5. Test representative role workflows.
6. Delete the verification database after acceptance.

A backup is not considered reliable until a real restoration test succeeds.

### Storage rules

- Never commit backup archives to Git.
- Keep credentials outside the scripts.
- Store production backups outside the application server.
- Use approved encrypted storage.
- Restrict access to authorized administrators.
- Define retention and secure-deletion rules.


## Production deployment and initial setup

## OYERA Production Deployment Guide

### Architecture

The production deployment contains three services:

1. `caddy` terminates HTTPS and serves uploaded media.
2. `app` runs Django through Gunicorn as a non-root user.
3. `db` runs PostgreSQL on an internal-only network.

Only Caddy publishes ports to the host. The application and database are not
directly exposed to the public network.

### Server requirements

Install:

- Docker Engine or Docker Desktop
- Docker Compose
- Git

For a public deployment:

- The domain must resolve to the server.
- TCP ports 80 and 443 must be reachable.
- The server must have persistent storage for Docker volumes.

### Create the production environment

Copy the template:

    cp .env.production.example .env.production

Generate three separate secrets:

    python - <<'PY'
    import secrets

    for name in (
        "DJANGO_SECRET_KEY",
        "POSTGRES_ADMIN_PASSWORD",
        "POSTGRES_PASSWORD",
    ):
        print(f"{name}={secrets.token_urlsafe(48)}")
    PY

Place the generated values in `.env.production`.

Never use the demonstration usernames or passwords in production.

### Validate the configuration

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      config --quiet

### Start the stack

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      up \
      --detach \
      --build

The application startup process:

1. Runs the Django system check.
2. Applies database migrations.
3. Collects static files.
4. Starts Gunicorn.

### Check service state

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      ps

All three services should be running. The database and application should
report a healthy status.

### Verify health endpoints

    curl --fail https://your-domain.example/health/live/

    curl --fail https://your-domain.example/health/ready/

The liveness endpoint confirms that the web process is available. The
readiness endpoint also confirms database connectivity.

### Inspect logs

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      logs \
      --tail 200

### Run the deployment security check

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      exec \
      --no-TTY \
      app \
      python src/manage.py check \
        --deploy \
        --fail-level WARNING

The command must report no warnings before acceptance.

### Create the first administrator

Do not run `reset_demo_data` in production.

Create the initial administrator interactively:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      exec app \
      python src/manage.py createsuperuser

Create ordinary employees through the OYERA employee-management interface and
assign each employee the minimum required role.

### HSTS rollout

Keep `DJANGO_SECURE_HSTS_SECONDS=0` during initial HTTPS verification.

After HTTPS, proxy handling, the domain, and intended subdomains are verified:

1. Begin with a short HSTS duration.
2. Observe the production deployment.
3. Increase the duration gradually.
4. Enable subdomains only when every subdomain supports HTTPS.
5. Enable preload only after permanent HTTPS readiness is confirmed.

### Persistent data

The following Docker volumes contain persistent information:

- `postgres_data`: PostgreSQL database
- `media_data`: user-uploaded files
- `caddy_data`: TLS certificates and Caddy state
- `caddy_config`: Caddy runtime configuration

Do not delete these volumes during routine deployment or shutdown.

### Database backup

Create a backup directory:

    mkdir -p backups

Create the database archive:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      exec \
      --no-TTY \
      app \
      scripts/db_backup.sh \
        /tmp/oyera-production.dump

Copy it to the host:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      cp \
      app:/tmp/oyera-production.dump \
      backups/oyera-production.dump

Store database archives as confidential information.

Uploaded media must be backed up separately from PostgreSQL.

### Application update

Before every update:

1. Create and validate a database backup.
2. Back up uploaded media.
3. Pull the reviewed release.
4. Rebuild the application image.
5. Verify migrations and service health.
6. Test login and one representative role workflow.

Update command:

    git pull --ff-only

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      up \
      --detach \
      --build

### Stop the deployment

Stop containers while retaining all persistent data:

    docker compose \
      --env-file .env.production \
      --file compose.production.yml \
      down

Never add `--volumes` during routine production shutdown. That option deletes
the database, media, and Caddy certificate volumes.


## Production deployment validation

## OYERA Production Deployment Validation

- Validation date: 2026-08-04
- Runtime: Docker Engine through Colima
- Architecture: ARM64
- Stack: Caddy, Django/Gunicorn, PostgreSQL 17
- Result: PASS

### Image validation

- Production image built successfully.
- Image tag: `oyera-auto-service:release-candidate`
- Runtime account: `uid=10001(oyera)`
- The application does not run as root.

### Service validation

- PostgreSQL became healthy.
- Django became healthy.
- Caddy started and terminated local HTTPS.
- HTTP redirected to HTTPS.
- Liveness returned HTTP 200.
- Readiness returned HTTP 200 with database status `ok`.

### Django validation

- All migrations were applied.
- Static-file collection completed.
- Gunicorn started with two workers.
- The strict deployment check passed with no warnings.
- Hardened HSTS target:
  - `SECURE_HSTS_SECONDS=31536000`
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
  - `SECURE_HSTS_PRELOAD=True`

### Database validation

- Django connected as `oyera_app`.
- Database name: `oyera_service`
- Application role permissions:
  - Superuser: false
  - Create database: false
  - Create role: false
  - Replication: false
  - Bypass row-level security: false

### Storage validation

- Hashed static asset returned HTTP 200.
- Persistent media was written by Django and read through Caddy.
- Temporary media evidence was removed.
- PostgreSQL custom-format backup was created and validated.

### Administrator validation

- A production superuser was created through `createsuperuser`.
- The account was active, staff-enabled, and a superuser.
- The temporary audit database and volumes were removed after testing.

### Acceptance

**PASS — the production container stack satisfies the Phase 17.1 deployment
and initial-setup acceptance criteria.**


## Defect reporting procedure

Use the editable template:

`docs/handover/uat-defect-report-template.md`

## OYERA UAT Defect Report

| Field | Entry |
| --- | --- |
| Defect ID | |
| Date and time | |
| Tester | |
| Role/account | |
| UAT case | |
| Environment | |
| Browser and version | |
| Page URL | |
| Severity | Critical / High / Medium / Low |
| Status | Open / Retest / Closed |

### Summary

Describe what failed in one sentence.

### Exact steps to reproduce

1.
2.
3.

### Input values used

Record every value entered by the tester.

### Expected result

Copy the expected result from the relevant role guide.

### Actual result

Describe the exact visible and stored result.

### Evidence

- Screenshot filename:
- CSV filename:
- Server-log extract:
- Relevant database verification:

### Reset and retest record

- Demo database reset performed:
- Fix version/commit:
- Retest result:
- Closed by:


## Final acceptance checklist

## OYERA Final Acceptance Checklist

### Technical acceptance

- [ ] Production deployment guide reviewed.
- [ ] Production environment values are unique and secret.
- [ ] HTTPS and domain configuration verified.
- [ ] Database backup created before deployment.
- [ ] Restore procedure tested.
- [ ] Health endpoints return expected results.
- [ ] Static files load correctly.
- [ ] Uploaded media uses persistent storage.
- [ ] All migrations are applied.
- [ ] Production administrator account created securely.

### Functional acceptance

- [ ] Administrator guide accepted.
- [ ] Manager guide accepted.
- [ ] Receptionist guide accepted.
- [ ] Senior Technician guide accepted.
- [ ] Technician guide accepted.
- [ ] Cashier guide accepted.
- [ ] All 32 UAT cases reviewed.
- [ ] Evidence files reviewed.
- [ ] Open defects documented and accepted.

### Handover acceptance

| Responsibility | Name | Signature | Date |
| --- | --- | --- | --- |
| Tester | | | |
| Business representative | | | |
| System owner | | | |
| Developer | | | |


## Evidence inventory

The master PDF includes all 41 verified screenshots.

The following CSV evidence files are retained in the repository:

- `docs/uat/evidence/csv/UAT-ADM-03-customer-finance.csv`
- `docs/uat/evidence/csv/UAT-ADM-03-inventory-activity.csv`
- `docs/uat/evidence/csv/UAT-ADM-03-purchasing-activity.csv`
- `docs/uat/evidence/csv/UAT-ADM-03-workshop-operations.csv`
- `docs/uat/evidence/csv/UAT-CAS-01-customer-finance.csv`
- `docs/uat/evidence/csv/UAT-CAS-01-purchasing-activity.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-customer-finance.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-inventory-activity.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-purchasing-activity.csv`
- `docs/uat/evidence/csv/UAT-MGR-02-workshop-operations.csv`

## Regeneration

Run:

```bash
DJANGO_SETTINGS_MODULE=config.settings.development \
PYTHONPATH=src \
python scripts/generate_handover_package.py
```

The generated PDFs are written to:

`docs/handover/pdf/`
