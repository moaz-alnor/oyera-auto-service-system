# OYERA UAT Baseline

This document records the exact database, roles, credentials,
permissions, and dashboard links used to begin UAT.

## Demo accounts

| Role | Username | Password | Login | Dashboard |
| --- | --- | --- | ---: | ---: |
| Administrator | `admin` | `AdminDemo123!` | PASS | 200 |
| Manager | `manager` | `ManagerDemo123!` | PASS | 200 |
| Receptionist | `receptionist` | `ReceptionDemo123!` | PASS | 200 |
| Senior Technician | `senior_technician` | `SeniorTechDemo123!` | PASS | 200 |
| Technician | `technician` | `TechnicianDemo123!` | PASS | 200 |
| Cashier | `cashier` | `CashierDemo123!` | PASS | 200 |

## Seeded business records

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

## Administrator

- Username: `admin`
- Password: `AdminDemo123!`
- Assigned group: `Administrator`
- Effective permissions: 224
- Visible dashboard links: 24

### Effective permissions

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

### Visible dashboard links

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

## Manager

- Username: `manager`
- Password: `ManagerDemo123!`
- Assigned group: `Manager`
- Effective permissions: 102
- Visible dashboard links: 23

### Effective permissions

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

### Visible dashboard links

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

## Receptionist

- Username: `receptionist`
- Password: `ReceptionDemo123!`
- Assigned group: `Receptionist`
- Effective permissions: 38
- Visible dashboard links: 18

### Effective permissions

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

### Visible dashboard links

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

## Senior Technician

- Username: `senior_technician`
- Password: `SeniorTechDemo123!`
- Assigned group: `Senior Technician`
- Effective permissions: 41
- Visible dashboard links: 15

### Effective permissions

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

### Visible dashboard links

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

## Technician

- Username: `technician`
- Password: `TechnicianDemo123!`
- Assigned group: `Technician`
- Effective permissions: 23
- Visible dashboard links: 9

### Effective permissions

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

### Visible dashboard links

- `/`
- `/inventory/`
- `/inventory/?low_stock=on`
- `/jobs/`
- `/products/`
- `/quotations/`
- `/services/`
- `/vehicles/`
- `/workshop/`

## Cashier

- Username: `cashier`
- Password: `CashierDemo123!`
- Assigned group: `Cashier`
- Effective permissions: 31
- Visible dashboard links: 21

### Effective permissions

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

### Visible dashboard links

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

## Baseline result

**PASS — all six accounts authenticated and all dashboards returned HTTP 200.**
