# Tripletex API — Slim Endpoint Index

Only endpoints relevant to competition tasks.

| Method | Path | Summary |
|--------|------|---------|
| GET | `/employee` | Find employees corresponding with sent data. |
| POST | `/employee` | Create one employee. |
| GET | `/employee/{id}` | Get employee by ID. |
| PUT | `/employee/{id}` | Update employee. |
| GET | `/employee/employment` | Find all employments for employee. |
| POST | `/employee/employment` | Create employment. |
| POST | `/employee/employment/details` | Create employment details. |
| PUT | `/employee/entitlement/:grantEntitlementsByTemplate` | Update employee entitlements. |
| GET | `/customer` | Find customers corresponding with sent data. |
| POST | `/customer` | Create customer. |
| GET | `/customer/{id}` | Find customer by ID. |
| PUT | `/customer/{id}` | Update customer. |
| GET | `/supplier` | Find suppliers corresponding with sent data. |
| POST | `/supplier` | Create supplier. |
| GET | `/supplier/{id}` | Get supplier by ID. |
| GET | `/product` | Find products corresponding with sent data. |
| POST | `/product` | Create one product. |
| GET | `/product/{id}` | Find product by ID. |
| GET | `/department` | Find departments corresponding with sent data. |
| POST | `/department` | Add new department. |
| GET | `/order` | Find orders corresponding with sent data. |
| POST | `/order` | Create order. |
| GET | `/order/{id}` | Get order by ID. |
| GET | `/order/orderline` | Get order line by ID. |
| POST | `/order/orderline` | Create order line. Supports creating multiple simultaneously. |
| POST | `/invoice` | Create invoice. |
| GET | `/invoice` | Find invoices corresponding with sent data. |
| GET | `/invoice/{id}` | Get invoice by ID. |
| PUT | `/invoice/{id}/:createCreditNote` | Creates a new Invoice representing a credit memo. |
| PUT | `/invoice/{id}/:send` | Send invoice by ID and target send type. |
| POST | `/invoice/{invoiceId}/:addPayment` | Register payment on invoice. |
| GET | `/invoice/paymentType` | Get payment types for outgoing invoices. |
| GET | `/supplierInvoice` | Find supplier invoices. |
| POST | `/supplierInvoice/{invoiceId}/:addPayment` | Register payment on supplier invoice. |
| PUT | `/supplierInvoice/voucher/{id}/postings` | Put debit postings. |
| POST | `/ledger/voucher` | Add new voucher. Also creates postings. |
| GET | `/ledger/voucher` | Find vouchers. |
| GET | `/ledger/voucherType` | Get voucher types. |
| GET | `/ledger/vatType` | Find vat types. |
| GET | `/ledger/account` | Find accounts corresponding with sent data. |
| POST | `/ledger/accountingDimensionName` | Create accounting dimension name. |
| POST | `/ledger/accountingDimensionValue` | Create accounting dimension value. |
| POST | `/salary/transaction` | Create a new salary transaction. |
| GET | `/salary/type` | Find salary types. |
| GET | `/salary/payslip` | Find payslips. |
| POST | `/travelExpense` | Create travel expense. |
| GET | `/travelExpense` | Find travel expenses. |
| POST | `/travelExpense/cost` | Create cost. |
| POST | `/travelExpense/perDiemCompensation` | Create per diem compensation. |
| GET | `/travelExpense/paymentType` | Get payment types for travel expenses. |
| GET | `/travelExpense/rate` | Find rates. |
| GET | `/travelExpense/rateCategory` | Find rate categories. |
| GET | `/travelExpense/zone` | Find travel expense zones. |
| POST | `/project` | Add new project. |
| GET | `/project` | Find projects. |
| POST | `/project/projectActivity` | Add project activity. |
| GET | `/activity` | Find activities. |
| POST | `/timesheet/entry` | Create timesheet entry. |
| GET | `/timesheet/entry` | Find timesheet entries. |
| POST | `/project/orderline` | Create project order line. |
| GET | `/currency` | Find currencies. |
| GET | `/country` | Find countries. |
| PUT | `/company` | Update company information. |
| DELETE | `/travelExpense/{id}` | Delete travel expense. |
| DELETE | `/invoice/{id}` | Delete invoice. |
