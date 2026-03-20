# Tripletex API — Endpoint Index

| Method | Path | Summary |
|--------|------|---------|
| GET | `/accountantDashboard/news` | Get public news articles |
| GET | `/accountantDashboard/news/tags` | Get all existing news tags |
| GET | `/accountingOffice/reconciliations/{reconciliationId}/control` | Returns a list of reconciliation controls with the given reconciliationId |
| PUT | `/accountingOffice/reconciliations/{reconciliationId}/control/:controlReconciliation` | Mark a reconciliation as controlled |
| PUT | `/accountingOffice/reconciliations/{reconciliationId}/control/:reconcile` | Mark a reconciliation as reconciled |
| PUT | `/accountingOffice/reconciliations/{reconciliationId}/control/:requestControl` | Request control of a reconciliation |
| GET | `/activity` | Find activities corresponding with sent data. |
| POST | `/activity` | Add activity. |
| GET | `/activity/>forTimeSheet` | Find applicable time sheet activities for an employee on a specific day. |
| POST | `/activity/list` | Add multiple activities. |
| GET | `/activity/{id}` | Find activity by ID. |
| GET | `/asset` | Find assets corresponding with sent data. |
| POST | `/asset` | Create one asset. |
| GET | `/asset/assetsExist` | Get if AssetOverview details is empty. |
| GET | `/asset/balanceAccountsSum` | Get balanceAccountsSum. |
| GET | `/asset/canDelete/{id}` | Validate delete asset |
| DELETE | `/asset/deleteImport` | [BETA] Delete most recent assets import. |
| DELETE | `/asset/deleteStartingBalance` | [BETA] Delete the asset starting balance. |
| POST | `/asset/duplicate/{id}` | Create copy of one asset |
| POST | `/asset/list` | Create several assets. |
| POST | `/asset/upload` | [BETA] Upload Excel file with Assets in the standard Tripletex defined format. |
| DELETE | `/asset/{id}` | Delete asset. |
| GET | `/asset/{id}` | Get asset by ID. |
| PUT | `/asset/{id}` | Update asset. |
| GET | `/asset/{id}/postings` | Get postings associated with asset |
| PUT | `/attestation/:addApprover` |  |
| GET | `/attestation/addApproverPermission` |  |
| GET | `/attestation/companyModules` | Get attestation company modules |
| POST | `/balance/reconciliation/annual/context` | Create a annualBalance reconciliation context for a customer |
| GET | `/balance/reconciliation/attachment/{attachmentId}/pdf` | Get an attached voucher as PDF |
| GET | `/balance/reconciliation/{reconciliationId}/account/{accountId}/vouchers` | Find vouchers for an account in the period of the balance reconciliation |
| GET | `/balanceSheet` | Get balance sheet (saldobalanse). |
| GET | `/bank` | Find bank corresponding with sent data. |
| GET | `/bank/reconciliation` | Find bank reconciliation corresponding with sent data. |
| POST | `/bank/reconciliation` | Post a bank reconciliation. |
| GET | `/bank/reconciliation/>last` | Get the last created reconciliation by account ID. |
| GET | `/bank/reconciliation/>lastClosed` | Get last closed reconciliation by account ID. |
| GET | `/bank/reconciliation/closedWithUnmatchedTransactions` | Get the last closed reconciliation with unmached transactions by account ID. |
| GET | `/bank/reconciliation/match` | Find bank reconciliation match corresponding with sent data. |
| POST | `/bank/reconciliation/match` | Create a bank reconciliation match. |
| PUT | `/bank/reconciliation/match/:suggest` | Suggest matches for a bank reconciliation by ID. |
| GET | `/bank/reconciliation/match/count` | Get the total number of matches |
| GET | `/bank/reconciliation/match/query` | [INTERNAL] Wildcard search. |
| DELETE | `/bank/reconciliation/match/{id}` | Delete a bank reconciliation match by ID. |
| GET | `/bank/reconciliation/match/{id}` | Get bank reconciliation match by ID. |
| PUT | `/bank/reconciliation/match/{id}` | Update a bank reconciliation match by ID. |
| GET | `/bank/reconciliation/matches/counter` | [BETA] Get number of matches since last page access. |
| POST | `/bank/reconciliation/matches/counter` | [BETA] Reset the number of matches after the page has been accessed. |
| GET | `/bank/reconciliation/paymentType` | Find payment type corresponding with sent data. |
| GET | `/bank/reconciliation/paymentType/{id}` | Get payment type by ID. |
| GET | `/bank/reconciliation/settings` | Get bank reconciliation settings. |
| POST | `/bank/reconciliation/settings` | Post bank reconciliation settings. |
| PUT | `/bank/reconciliation/settings/{id}` | Update bank reconciliation settings. |
| PUT | `/bank/reconciliation/transactions/unmatched:csv` | Get all unmatched transactions in csv format |
| DELETE | `/bank/reconciliation/{id}` | Delete bank reconciliation by ID. |
| GET | `/bank/reconciliation/{id}` | Get bank reconciliation. |
| PUT | `/bank/reconciliation/{id}` | Update a bank reconciliation. |
| PUT | `/bank/reconciliation/{id}/:adjustment` | Add an adjustment to reconciliation by ID. |
| GET | `/bank/statement` | Find bank statement corresponding with sent data. |
| POST | `/bank/statement/import` | Upload bank statement file. |
| GET | `/bank/statement/transaction` | Find bank transaction corresponding with sent data. |
| GET | `/bank/statement/transaction/{id}` | Get bank transaction by ID. |
| GET | `/bank/statement/transaction/{id}/details` | Get additional details about transaction by ID. |
| DELETE | `/bank/statement/{id}` | Delete bank statement by ID. |
| GET | `/bank/statement/{id}` | Get bank statement. |
| GET | `/bank/{id}` | Get bank. |
| PUT | `/company` | Update company information. |
| GET | `/company/>withLoginAccess` | Returns client customers (with accountant/auditor relation) where the current user has login access (proxy login). |
| GET | `/company/divisions` | [DEPRECATED] Find divisions. |
| GET | `/company/salesmodules` | [BETA] Get active sales modules. |
| POST | `/company/salesmodules` | [BETA] Add (activate) a new sales module. |
| GET | `/company/settings/altinn` | Find Altinn id for login in company. |
| PUT | `/company/settings/altinn` | Update AltInn id and password. |
| GET | `/company/{id}` | Find company by ID. |
| GET | `/contact` | Find contacts corresponding with sent data. |
| POST | `/contact` | Create contact. |
| DELETE | `/contact/list` | [BETA] Delete multiple contacts. |
| POST | `/contact/list` | Create multiple contacts. |
| GET | `/contact/{id}` | Get contact by ID. |
| PUT | `/contact/{id}` | Update contact. |
| GET | `/country` | Find countries corresponding with sent data. |
| GET | `/country/{id}` | Get country by ID. |
| GET | `/crm/prospect` | Find prospects corresponding with sent data. |
| GET | `/crm/prospect/{id}` | Get prospect by ID. |
| GET | `/currency` | Find currencies corresponding with sent data. |
| GET | `/currency/{fromCurrencyID}/exchangeRate` | Returns the amount in the company currency, where the input amount is in fromCurrency, using the newest exchange rate available for the given date |
| GET | `/currency/{fromCurrencyID}/{toCurrencyID}/exchangeRate` | Returns the amount in the specified currency, where the input amount is in fromCurrency, using the newest exchange rate available for the given date |
| GET | `/currency/{id}` | Get currency by ID. |
| GET | `/currency/{id}/rate` | Find currency exchange rate corresponding with sent data. |
| GET | `/customer` | Find customers corresponding with sent data. |
| POST | `/customer` | Create customer. Related customer addresses may also be created. |
| GET | `/customer/category` | Find customer/supplier categories corresponding with sent data. |
| POST | `/customer/category` | Add new customer/supplier category. |
| GET | `/customer/category/{id}` | Find customer/supplier category by ID. |
| PUT | `/customer/category/{id}` | Update customer/supplier category. |
| POST | `/customer/list` | [BETA] Create multiple customers. Related supplier addresses may also be created. |
| PUT | `/customer/list` | [BETA] Update multiple customers. Addresses can also be updated. |
| DELETE | `/customer/{id}` | [BETA] Delete customer by ID |
| GET | `/customer/{id}` | Get customer by ID. |
| PUT | `/customer/{id}` | Update customer. |
| GET | `/deliveryAddress` | Find addresses corresponding with sent data. |
| GET | `/deliveryAddress/{id}` | Get address by ID. |
| PUT | `/deliveryAddress/{id}` | Update address. |
| GET | `/department` | Find department corresponding with sent data. |
| POST | `/department` | Add new department. |
| POST | `/department/list` | Register new departments. |
| PUT | `/department/list` | Update multiple departments. |
| GET | `/department/query` | Wildcard search. |
| DELETE | `/department/{id}` | Delete department by ID |
| GET | `/department/{id}` | Get department by ID. |
| PUT | `/department/{id}` | Update department. |
| GET | `/division` | Get divisions. |
| POST | `/division` | Create division. |
| POST | `/division/list` | Create divisions. |
| PUT | `/division/list` | Update multiple divisions. |
| PUT | `/division/{id}` | Update division information. |
| GET | `/document/{id}` | [BETA] Get document by ID. |
| GET | `/document/{id}/content` | [BETA] Get content of document given by ID. |
| GET | `/documentArchive/account/{id}` | [BETA] Find documents archived associated with account object type. |
| POST | `/documentArchive/account/{id}` | [BETA] Upload file to Account Document Archive. |
| GET | `/documentArchive/customer/{id}` | [BETA] Find documents archived associated with customer object type. |
| POST | `/documentArchive/customer/{id}` | [BETA] Upload file to Customer Document Archive. |
| GET | `/documentArchive/dynamicControlForm/{id}` | [BETA] Find documents archived associated with control form object type. |
| POST | `/documentArchive/dynamicControlForm/{id}` | [BETA] Upload file to Control Form Document Archive. |
| GET | `/documentArchive/employee/{id}` | [BETA] Find documents archived associated with employee object type. |
| POST | `/documentArchive/employee/{id}` | [BETA] Upload file to Employee Document Archive. |
| GET | `/documentArchive/product/{id}` | [BETA] Find documents archived associated with product object type. |
| POST | `/documentArchive/product/{id}` | [BETA] Upload file to Product Document Archive. |
| GET | `/documentArchive/project/{id}` | [BETA] Find documents archived associated with project object type. |
| POST | `/documentArchive/project/{id}` | [BETA] Upload file to Project Document Archive. |
| POST | `/documentArchive/reception` | [BETA] Upload a file to the document archive reception. Send as multipart form. |
| GET | `/documentArchive/supplier/{id}` | [BETA] Find documents archived associated with supplier object type. |
| POST | `/documentArchive/supplier/{id}` | [BETA] Upload file to Supplier Document Archive. |
| DELETE | `/documentArchive/{id}` | [BETA] Delete document archive. |
| PUT | `/documentArchive/{id}` | [BETA] Update document archive. |
| GET | `/employee` | Find employees corresponding with sent data. |
| POST | `/employee` | Create one employee. |
| GET | `/employee/category` | Find employee category corresponding with sent data. |
| POST | `/employee/category` | Create a new employee category. |
| DELETE | `/employee/category/list` | Delete multiple employee categories |
| POST | `/employee/category/list` | Create new employee categories. |
| PUT | `/employee/category/list` | Update multiple employee categories. |
| DELETE | `/employee/category/{id}` | Delete employee category by ID |
| GET | `/employee/category/{id}` | Get employee category by ID. |
| PUT | `/employee/category/{id}` | Update employee category information. |
| GET | `/employee/employment` | Find all employments for employee. |
| POST | `/employee/employment` | Create employment. |
| GET | `/employee/employment/details` | Find all employmentdetails for employment. |
| POST | `/employee/employment/details` | Create employment details. |
| GET | `/employee/employment/details/{id}` | Find employment details by ID. |
| PUT | `/employee/employment/details/{id}` | Update employment details. |
| GET | `/employee/employment/employmentType` | Find all employment type IDs. |
| GET | `/employee/employment/employmentType/employmentEndReasonType` | Find all employment end reason type IDs. |
| GET | `/employee/employment/employmentType/employmentFormType` | Find all employment form type IDs. |
| GET | `/employee/employment/employmentType/maritimeEmploymentType` | Find all maritime employment type IDs. |
| GET | `/employee/employment/employmentType/salaryType` | Find all salary type IDs. |
| GET | `/employee/employment/employmentType/scheduleType` | Find all schedule type IDs. |
| GET | `/employee/employment/leaveOfAbsence` | Find all leave of absence corresponding with the sent data. |
| POST | `/employee/employment/leaveOfAbsence` | Create leave of absence. |
| POST | `/employee/employment/leaveOfAbsence/list` | Create multiple leave of absences. |
| GET | `/employee/employment/leaveOfAbsence/{id}` | Find leave of absence by ID. |
| PUT | `/employee/employment/leaveOfAbsence/{id}` | Update leave of absence. |
| GET | `/employee/employment/leaveOfAbsenceType` | Find all leave of absence type IDs. |
| GET | `/employee/employment/occupationCode` | Find all profession codes. |
| GET | `/employee/employment/occupationCode/{id}` | Get occupation by ID. |
| GET | `/employee/employment/remunerationType` | Find all remuneration type IDs. |
| GET | `/employee/employment/workingHoursScheme` | Find working hours scheme ID. |
| GET | `/employee/employment/{id}` | Find employment by ID. |
| PUT | `/employee/employment/{id}` | Update employemnt. |
| GET | `/employee/entitlement` | Find all entitlements for user. |
| PUT | `/employee/entitlement/:grantClientEntitlementsByTemplate` | [BETA] Update employee entitlements in client account. |
| PUT | `/employee/entitlement/:grantEntitlementsByTemplate` | [BETA] Update employee entitlements. |
| GET | `/employee/entitlement/client` | [BETA] Find all entitlements at client for user. |
| GET | `/employee/entitlement/{id}` | Get entitlement by ID. |
| GET | `/employee/hourlyCostAndRate` | Find all hourly cost and rates for employee. |
| POST | `/employee/hourlyCostAndRate` | Create hourly cost and rate. |
| GET | `/employee/hourlyCostAndRate/{id}` | Find hourly cost and rate by ID. |
| PUT | `/employee/hourlyCostAndRate/{id}` | Update hourly cost and rate. |
| POST | `/employee/list` | Create several employees. |
| GET | `/employee/nextOfKin` | Find all next of kin for employee. |
| POST | `/employee/nextOfKin` | Create next of kin. |
| GET | `/employee/nextOfKin/{id}` | Find next of kin by ID. |
| PUT | `/employee/nextOfKin/{id}` | Update next of kin. |
| GET | `/employee/preferences` | Find employee preferences corresponding with sent data. |
| PUT | `/employee/preferences/:changeLanguage` | Change current employees language to the given language |
| GET | `/employee/preferences/>loggedInEmployeePreferences` | Get employee preferences for current user |
| PUT | `/employee/preferences/list` | Update multiple employee preferences. |
| PUT | `/employee/preferences/{id}` | Update employee preferences information. |
| GET | `/employee/searchForEmployeesAndContacts` | Get employees and contacts by parameters. Include contacts by default. |
| GET | `/employee/standardTime` | Find all standard times for employee. |
| POST | `/employee/standardTime` | Create standard time. |
| GET | `/employee/standardTime/byDate` | Find standard time for employee by date. |
| GET | `/employee/standardTime/{id}` | Find standard time by ID. |
| PUT | `/employee/standardTime/{id}` | Update standard time. |
| GET | `/employee/{id}` | Get employee by ID. |
| PUT | `/employee/{id}` | Update employee. |
| GET | `/event` | [BETA] Get all (WebHook) event keys. |
| GET | `/event/subscription` | [BETA] Find all ongoing subscriptions. |
| POST | `/event/subscription` | [BETA] Create a new subscription for current EmployeeToken. |
| DELETE | `/event/subscription/list` | [BETA] Delete multiple subscriptions. |
| POST | `/event/subscription/list` | [BETA] Create multiple subscriptions for current EmployeeToken. |
| PUT | `/event/subscription/list` | [BETA] Update multiple subscription. |
| DELETE | `/event/subscription/{id}` | [BETA] Delete the given subscription. |
| GET | `/event/subscription/{id}` | [BETA] Get subscription by ID. |
| PUT | `/event/subscription/{id}` | [BETA] Change a current subscription, based on id. |
| GET | `/event/{eventType}` | [BETA] Get example webhook payload |
| POST | `/incomingInvoice` | [BETA] create an invoice |
| GET | `/incomingInvoice/search` | [BETA] Get a list of invoices |
| GET | `/incomingInvoice/{voucherId}` | [BETA] Get an invoice by voucherId |
| PUT | `/incomingInvoice/{voucherId}` | [BETA] update an invoice by voucherId |
| POST | `/incomingInvoice/{voucherId}/addPayment` | [BETA] create a payment for voucher/invoice |
| GET | `/internal/debtCollector` | Get last select debt collector |
| DELETE | `/internal/debtCollector/deactivate` | Deactivate debt collector relation |
| PUT | `/internal/nhoAdmin/:abort` | Aborts all scheduled NHO membership events |
| GET | `/inventory` | Find inventory corresponding with sent data. |
| POST | `/inventory` | Create new inventory. |
| GET | `/inventory/inventories` | Find inventories corresponding with sent data. |
| GET | `/inventory/location` | Find inventory locations by inventory ID. Only available for Logistics Basic. |
| POST | `/inventory/location` | Create new inventory location. Only available for Logistics Basic. |
| DELETE | `/inventory/location/list` | Delete inventory location. Only available for Logistics Basic. |
| POST | `/inventory/location/list` | Add multiple inventory locations. Only available for Logistics Basic. |
| PUT | `/inventory/location/list` | Update multiple inventory locations. Only available for Logistics Basic. |
| DELETE | `/inventory/location/{id}` | Delete inventory location. Only available for Logistics Basic. |
| GET | `/inventory/location/{id}` | Get inventory location by ID. Only available for Logistics Basic. |
| PUT | `/inventory/location/{id}` | Update inventory location. Only available for Logistics Basic. |
| GET | `/inventory/stocktaking` | Find stocktaking corresponding with sent data. |
| POST | `/inventory/stocktaking` | Create new stocktaking. |
| GET | `/inventory/stocktaking/productline` | Find all order lines by stocktaking ID. |
| POST | `/inventory/stocktaking/productline` | Create order line. When creating several order lines, use /list for better performance. |
| DELETE | `/inventory/stocktaking/productline/{id}` | Delete order line. |
| GET | `/inventory/stocktaking/productline/{id}` | Get order line by ID. |
| PUT | `/inventory/stocktaking/productline/{id}` | Update order line. |
| PUT | `/inventory/stocktaking/productline/{id}/:changeLocation` | [Beta] Change location on order line. |
| DELETE | `/inventory/stocktaking/{id}` | Delete stocktaking. |
| GET | `/inventory/stocktaking/{id}` | Get stocktaking by ID. |
| PUT | `/inventory/stocktaking/{id}` | Update stocktaking. |
| DELETE | `/inventory/{id}` | Delete inventory. |
| GET | `/inventory/{id}` | Get inventory by ID. |
| PUT | `/inventory/{id}` | Update inventory. |
| GET | `/invoice` | Find invoices corresponding with sent data. Includes charged outgoing invoices only. |
| POST | `/invoice` | Create invoice. Related Order and OrderLines can be created first, or included as new objects inside the Invoice. |
| GET | `/invoice/details` | Find ProjectInvoiceDetails corresponding with sent data. |
| GET | `/invoice/details/{id}` | Get ProjectInvoiceDetails by ID. |
| POST | `/invoice/list` | [BETA] Create multiple invoices. Max 100 at a time. |
| GET | `/invoice/paymentType` | Find payment type corresponding with sent data. |
| GET | `/invoice/paymentType/{id}` | Get payment type by ID. |
| GET | `/invoice/{id}` | Get invoice by ID. |
| PUT | `/invoice/{id}/:createCreditNote` | Creates a new Invoice representing a credit memo that nullifies the given invoice. Updates this invoice and any pre-existing inverse invoice. |
| PUT | `/invoice/{id}/:createReminder` | Create invoice reminder and sends it by the given dispatch type. Supports the reminder types SOFT_REMINDER, REMINDER and NOTICE_OF_DEBT_COLLECTION. DispatchType NETS_PRINT must have type NOTICE_OF_... |
| PUT | `/invoice/{id}/:payment` | Update invoice. The invoice is updated with payment information. The amount is in the invoice’s currency. |
| PUT | `/invoice/{id}/:send` | Send invoice by ID and sendType. Optionally override email recipient. |
| GET | `/invoice/{invoiceId}/pdf` | Get invoice document by invoice ID. |
| GET | `/invoiceRemark/{id}` | Get invoice remark by ID. |
| GET | `/ledger` | Get ledger (hovedbok). |
| GET | `/ledger/account` | Find accounts corresponding with sent data. |
| POST | `/ledger/account` | Create a new account. |
| DELETE | `/ledger/account/list` | Delete multiple accounts. |
| POST | `/ledger/account/list` | Create several accounts. |
| PUT | `/ledger/account/list` | Update multiple accounts. |
| DELETE | `/ledger/account/{id}` | Delete account. |
| GET | `/ledger/account/{id}` | Get account by ID. |
| PUT | `/ledger/account/{id}` | Update account. |
| GET | `/ledger/accountingDimensionName` | Get all accounting dimension names. |
| POST | `/ledger/accountingDimensionName` | Create a new free (aka 'user defined') accounting dimension |
| GET | `/ledger/accountingDimensionName/search` | Search for accounting dimension names according to criteria. |
| DELETE | `/ledger/accountingDimensionName/{id}` | Delete an accounting dimension name by ID |
| GET | `/ledger/accountingDimensionName/{id}` | Get a single accounting dimension name by ID |
| PUT | `/ledger/accountingDimensionName/{id}` | Update an accounting dimension |
| POST | `/ledger/accountingDimensionValue` | Create a new value for one of the free (aka 'user defined') accounting dimensions |
| PUT | `/ledger/accountingDimensionValue/list` | Update accounting dimension values |
| GET | `/ledger/accountingDimensionValue/search` | Search for accounting dimension values according to criteria. |
| DELETE | `/ledger/accountingDimensionValue/{id}` | Delete an accounting dimension value.  Values that have been used in postings can not be deleted. |
| GET | `/ledger/accountingDimensionValue/{id}` | Find accounting dimension values by ID. |
| GET | `/ledger/accountingPeriod` | Find accounting periods corresponding with sent data. |
| GET | `/ledger/accountingPeriod/{id}` | Get accounting period by ID. |
| GET | `/ledger/annualAccount` | Find annual accounts corresponding with sent data. |
| GET | `/ledger/annualAccount/{id}` | Get annual account by ID. |
| GET | `/ledger/closeGroup` | Find close groups corresponding with sent data. |
| GET | `/ledger/closeGroup/{id}` | Get close group by ID. |
| GET | `/ledger/openPost` | Find open posts corresponding with sent data. |
| GET | `/ledger/paymentTypeOut` | [BETA] Gets payment types for outgoing payments |
| POST | `/ledger/paymentTypeOut` | [BETA] Create new payment type for outgoing payments |
| POST | `/ledger/paymentTypeOut/list` | [BETA] Create multiple payment types for outgoing payments at once |
| PUT | `/ledger/paymentTypeOut/list` | [BETA] Update multiple payment types for outgoing payments at once |
| DELETE | `/ledger/paymentTypeOut/{id}` | [BETA] Delete payment type for outgoing payments by ID. |
| GET | `/ledger/paymentTypeOut/{id}` | [BETA] Get payment type for outgoing payments by ID. |
| PUT | `/ledger/paymentTypeOut/{id}` | [BETA] Update existing payment type for outgoing payments |
| GET | `/ledger/posting` | Find postings corresponding with sent data. |
| PUT | `/ledger/posting/:closePostings` | Close postings. |
| GET | `/ledger/posting/openPost` | Find open posts corresponding with sent data. |
| GET | `/ledger/posting/{id}` | Find postings by ID. |
| GET | `/ledger/postingByDate` | Get postings by date range with pagination. Returns the same PostingDTO as /ledger/posting. Simplified endpoint for better performance. Fields and Changes are not supported. Token must have access ... |
| GET | `/ledger/postingRules` | Get posting rules for current company.  The posting rules defined which accounts from the chart of accounts that are used for postings when the system creates postings. |
| GET | `/ledger/vatSettings` | Get VAT settings for the logged in company. |
| PUT | `/ledger/vatSettings` | Update VAT settings for the logged in company. |
| GET | `/ledger/vatType` | Find vat types corresponding with sent data. |
| PUT | `/ledger/vatType/createRelativeVatType` | Create a new relative VAT Type. These are used if the company has 'forholdsmessig fradrag for inngående MVA'. |
| GET | `/ledger/vatType/{id}` | Get vat type by ID. |
| GET | `/ledger/voucher` | Find vouchers corresponding with sent data. |
| POST | `/ledger/voucher` | Add new voucher. IMPORTANT: Also creates postings. Only the gross amounts will be used. Amounts should be rounded to 2 decimals. |
| GET | `/ledger/voucher/>externalVoucherNumber` | Find vouchers based on the external voucher number. |
| GET | `/ledger/voucher/>nonPosted` | Find non-posted vouchers. |
| GET | `/ledger/voucher/>voucherReception` | Find vouchers in voucher reception. |
| PUT | `/ledger/voucher/historical/:closePostings` | [BETA] Close postings. |
| PUT | `/ledger/voucher/historical/:reverseHistoricalVouchers` | [BETA] Deletes all historical vouchers. Requires the "All vouchers" and "Advanced Voucher" permissions. |
| POST | `/ledger/voucher/historical/employee` | [BETA] Create one employee, based on import from external system. Validation is less strict, ie. employee department isn't required. |
| POST | `/ledger/voucher/historical/historical` | API endpoint for creating historical vouchers. These are vouchers created outside Tripletex, and should be from closed accounting years. The intended usage is to get access to historical transcatio... |
| POST | `/ledger/voucher/historical/{voucherId}/attachment` | Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). Valid document formats are PDF, PNG, JPEG and TIFF... |
| POST | `/ledger/voucher/importDocument` | Upload a document to create one or more vouchers. Valid document formats are PDF, PNG, JPEG and TIFF. EHF/XML is possible with agreement with Tripletex. Send as multipart form. |
| POST | `/ledger/voucher/importGbat10` | Import GBAT10. Send as multipart form. |
| PUT | `/ledger/voucher/list` | Update multiple vouchers. Postings with guiRow==0 will be deleted and regenerated. |
| DELETE | `/ledger/voucher/openingBalance` | [BETA] Delete the opening balance. The correction voucher will also be deleted |
| GET | `/ledger/voucher/openingBalance` | [BETA] Get the voucher for the opening balance. |
| POST | `/ledger/voucher/openingBalance` | [BETA] Add an opening balance on the given date.  All movements before this date will be 'zeroed out' in a separate correction voucher. The opening balance must have the first day of a month as the... |
| GET | `/ledger/voucher/openingBalance/>correctionVoucher` | [BETA] Get the correction voucher for the opening balance. |
| DELETE | `/ledger/voucher/{id}` | Delete voucher by ID. |
| GET | `/ledger/voucher/{id}` | Get voucher by ID. |
| PUT | `/ledger/voucher/{id}` | Update voucher. Postings with guiRow==0 will be deleted and regenerated. |
| PUT | `/ledger/voucher/{id}/:reverse` | Reverses the voucher, and returns the reversed voucher. Supports reversing most voucher types, except salary transactions. |
| PUT | `/ledger/voucher/{id}/:sendToInbox` | Send voucher to inbox. |
| PUT | `/ledger/voucher/{id}/:sendToLedger` | Send voucher to ledger. |
| GET | `/ledger/voucher/{id}/options` | Returns a data structure containing meta information about operations that are available for this voucher. Currently only implemented for DELETE: It is possible to check if the voucher is deletable. |
| DELETE | `/ledger/voucher/{voucherId}/attachment` | Delete attachment. |
| POST | `/ledger/voucher/{voucherId}/attachment` | Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). Valid document formats are PDF, PNG, JPEG and TIFF... |
| GET | `/ledger/voucher/{voucherId}/pdf` | Get PDF representation of voucher by ID. |
| POST | `/ledger/voucher/{voucherId}/pdf/{fileName}` | [DEPRECATED] Use POST ledger/voucher/{voucherId}/attachment instead. |
| GET | `/ledger/voucherType` | Find voucher types corresponding with sent data. |
| GET | `/ledger/voucherType/{id}` | Get voucher type by ID. |
| GET | `/municipality` | Get municipalities. |
| GET | `/municipality/query` | [BETA] Wildcard search. |
| GET | `/order` | Find orders corresponding with sent data. |
| POST | `/order` | Create order. |
| PUT | `/order/:invoiceMultipleOrders` | [BETA] Charges a single customer invoice from multiple orders. The orders must be to the same customer, currency, due date, receiver email, attn. and smsNotificationNumber |
| POST | `/order/list` | [BETA] Create multiple Orders with OrderLines. Max 100 at a time. |
| GET | `/order/orderConfirmation/{orderId}/pdf` | Get PDF representation of order by ID. |
| GET | `/order/orderGroup` | Find orderGroups corresponding with sent data. |
| POST | `/order/orderGroup` | [Beta] Post orderGroup. |
| PUT | `/order/orderGroup` | [Beta] Put orderGroup. |
| DELETE | `/order/orderGroup/{id}` | Delete orderGroup by ID. |
| GET | `/order/orderGroup/{id}` | Get orderGroup by ID. A orderGroup is a way to group orderLines, and add comments and subtotals |
| POST | `/order/orderline` | Create order line. When creating several order lines, use /list for better performance. |
| POST | `/order/orderline/list` | Create multiple order lines. |
| GET | `/order/orderline/orderLineTemplate` | [BETA] Get order line template from order and product |
| DELETE | `/order/orderline/{id}` | [BETA] Delete order line by ID. |
| GET | `/order/orderline/{id}` | Get order line by ID. |
| PUT | `/order/orderline/{id}` | [BETA] Put order line |
| PUT | `/order/orderline/{id}/:pickLine` | [BETA] Pick order line. This is only available for customers who have Logistics and who activated the available inventory functionality. |
| PUT | `/order/orderline/{id}/:unpickLine` | [BETA] Unpick order line.This is only available for customers who have Logistics and who activated the available inventory functionality. |
| GET | `/order/packingNote/{orderId}/pdf` | Get PDF representation of packing note by ID. |
| PUT | `/order/sendInvoicePreview/{orderId}` | Send Invoice Preview to customer by email. |
| PUT | `/order/sendOrderConfirmation/{orderId}` | Send Order Confirmation to customer by email. |
| PUT | `/order/sendPackingNote/{orderId}` | Send Packing Note to customer by email. |
| DELETE | `/order/{id}` | Delete order. |
| GET | `/order/{id}` | Get order by ID. |
| PUT | `/order/{id}` | Update order. |
| PUT | `/order/{id}/:approveSubscriptionInvoice` | To create a subscription invoice, first create a order with the subscription enabled, then approve it with this method. This approves the order for subscription invoicing. |
| PUT | `/order/{id}/:attach` | Attach document to specified order ID. |
| PUT | `/order/{id}/:invoice` | Create new invoice or subscription invoice from order. |
| PUT | `/order/{id}/:unApproveSubscriptionInvoice` | Unapproves the order for subscription invoicing. |
| GET | `/pension` | Find countries corresponding with sent data. |
| GET | `/pickupPoint` | [DEPRECATED] Search pickup points. |
| GET | `/pickupPoint/{id}` | [DEPRECATED] Find pickup point by ID. |
| GET | `/platformAgnostic/bank/onboarding/fetchOdpCustomerId` |  |
| GET | `/product` | Find products corresponding with sent data. |
| POST | `/product` | Create new product. |
| GET | `/product/discountGroup` | Find discount groups corresponding with sent data. |
| GET | `/product/discountGroup/{id}` | Get discount group by ID. |
| GET | `/product/external` | [BETA] Find external products corresponding with sent data. The sorting-field is not in use on this endpoint. |
| GET | `/product/external/{id}` | [BETA] Get external product by ID. |
| GET | `/product/group` | Find product group with sent data. Only available for Logistics Basic. |
| POST | `/product/group` | Create new product group. Only available for Logistics Basic. |
| DELETE | `/product/group/list` | Delete multiple product groups. Only available for Logistics Basic. |
| POST | `/product/group/list` | Add multiple products groups. Only available for Logistics Basic. |
| PUT | `/product/group/list` | Update a list of product groups. Only available for Logistics Basic. |
| GET | `/product/group/query` | Wildcard search. Only available for Logistics Basic. |
| DELETE | `/product/group/{id}` | Delete product group. Only available for Logistics Basic. |
| GET | `/product/group/{id}` | Find product group by ID. Only available for Logistics Basic. |
| PUT | `/product/group/{id}` | Update product group. Only available for Logistics Basic. |
| GET | `/product/groupRelation` | Find product group relation with sent data. Only available for Logistics Basic. |
| POST | `/product/groupRelation` | Create new product group relation. Only available for Logistics Basic. |
| DELETE | `/product/groupRelation/list` | Delete multiple product group relations. Only available for Logistics Basic. |
| POST | `/product/groupRelation/list` | Add multiple products group relations. Only available for Logistics Basic. |
| DELETE | `/product/groupRelation/{id}` | Delete product group relation. Only available for Logistics Basic. |
| GET | `/product/groupRelation/{id}` | Find product group relation by ID. Only available for Logistics Basic. |
| GET | `/product/inventoryLocation` | Find inventory locations by product ID. Only available for Logistics Basic. |
| POST | `/product/inventoryLocation` | Create new product inventory location. Only available for Logistics Basic. |
| POST | `/product/inventoryLocation/list` | Add multiple product inventory locations. Only available for Logistics Basic. |
| PUT | `/product/inventoryLocation/list` | Update multiple product inventory locations. Only available for Logistics Basic. |
| DELETE | `/product/inventoryLocation/{id}` | Delete product inventory location. Only available for Logistics Basic. |
| GET | `/product/inventoryLocation/{id}` | Get inventory location by ID. Only available for Logistics Basic. |
| PUT | `/product/inventoryLocation/{id}` | Update product inventory location. Only available for Logistics Basic. |
| POST | `/product/list` | Add multiple products. |
| PUT | `/product/list` | Update a list of products. |
| GET | `/product/logisticsSettings` | Get logistics settings for the logged in company. |
| PUT | `/product/logisticsSettings` | Update logistics settings for the logged in company. |
| GET | `/product/productPrice` | Find prices for a product. Only available for Logistics Basic. |
| GET | `/product/supplierProduct` | Find products corresponding with sent data. |
| POST | `/product/supplierProduct` | Create new supplierProduct. |
| POST | `/product/supplierProduct/getSupplierProductsByIds` | Find the products by ids. Method was added as a POST because GET request header has a maximum size that we can exceed with customers that a lot of products. |
| POST | `/product/supplierProduct/list` | Create list of new supplierProduct. |
| PUT | `/product/supplierProduct/list` | Update a list of supplierProduct. |
| DELETE | `/product/supplierProduct/{id}` | Delete supplierProduct. |
| GET | `/product/supplierProduct/{id}` | Get supplierProduct by ID. |
| PUT | `/product/supplierProduct/{id}` | Update supplierProduct. |
| GET | `/product/unit` | Find product units corresponding with sent data. |
| POST | `/product/unit` | Create new product unit. |
| POST | `/product/unit/list` | Create multiple product units. |
| PUT | `/product/unit/list` | Update list of product units. |
| GET | `/product/unit/master` | Find product units master corresponding with sent data. |
| GET | `/product/unit/master/{id}` | Get product unit master by ID. |
| GET | `/product/unit/query` | Wildcard search. |
| DELETE | `/product/unit/{id}` | Delete product unit by ID. |
| GET | `/product/unit/{id}` | Get product unit by ID. |
| PUT | `/product/unit/{id}` | Update product unit. |
| DELETE | `/product/{id}` | Delete product. |
| GET | `/product/{id}` | Get product by ID. |
| PUT | `/product/{id}` | Update product. |
| DELETE | `/product/{id}/image` | Delete image. |
| POST | `/product/{id}/image` | Upload image to product. Existing image on product will be replaced if exists |
| DELETE | `/project` | [BETA] Delete multiple projects. |
| GET | `/project` | Find projects corresponding with sent data. |
| POST | `/project` | Add new project. |
| GET | `/project/>forTimeSheet` | Find projects applicable for time sheet registration on a specific day. |
| GET | `/project/batchPeriod/budgetStatusByProjectIds` | Get the budget status for the projects in the specific period. |
| GET | `/project/batchPeriod/invoicingReserveByProjectIds` | Get the invoicing reserve for the projects in the specific period. |
| GET | `/project/category` | Find project categories corresponding with sent data. |
| POST | `/project/category` | Add new project category. |
| GET | `/project/category/{id}` | Find project category by ID. |
| PUT | `/project/category/{id}` | Update project category. |
| GET | `/project/controlForm` | [BETA] Get project control forms by project ID. |
| GET | `/project/controlForm/{id}` | [BETA] Get project control form by ID. |
| GET | `/project/controlFormType` | [BETA] Get project control form types |
| GET | `/project/controlFormType/{id}` | [BETA] Get project control form type by ID. |
| PUT | `/project/dynamicControlForm/{id}/:copyFieldValuesFromLastEditedForm` | Into each section in the specified form that only has empty or default values, and copyFieldValuesByDefault set as true in the form's template, copy field values from the equivalent section in the ... |
| GET | `/project/hourlyRates` | Find project hourly rates corresponding with sent data. |
| POST | `/project/hourlyRates` | Create a project hourly rate. |
| DELETE | `/project/hourlyRates/deleteByProjectIds` | Delete project hourly rates by project id. |
| DELETE | `/project/hourlyRates/list` | Delete project hourly rates. |
| POST | `/project/hourlyRates/list` | Create multiple project hourly rates. |
| PUT | `/project/hourlyRates/list` | Update multiple project hourly rates. |
| GET | `/project/hourlyRates/projectSpecificRates` | Find project specific rates corresponding with sent data. |
| POST | `/project/hourlyRates/projectSpecificRates` | Create new project specific rate. |
| DELETE | `/project/hourlyRates/projectSpecificRates/list` | Delete project specific rates. |
| POST | `/project/hourlyRates/projectSpecificRates/list` | Create multiple new project specific rates. |
| PUT | `/project/hourlyRates/projectSpecificRates/list` | Update multiple project specific rates. |
| DELETE | `/project/hourlyRates/projectSpecificRates/{id}` | Delete project specific rate |
| GET | `/project/hourlyRates/projectSpecificRates/{id}` | Find project specific rate by ID. |
| PUT | `/project/hourlyRates/projectSpecificRates/{id}` | Update a project specific rate. |
| PUT | `/project/hourlyRates/updateOrAddHourRates` | Update or add the same project hourly rate from project overview. |
| DELETE | `/project/hourlyRates/{id}` | Delete Project Hourly Rate |
| GET | `/project/hourlyRates/{id}` | Find project hourly rate by ID. |
| PUT | `/project/hourlyRates/{id}` | Update a project hourly rate. |
| POST | `/project/import` | Upload project import file. |
| DELETE | `/project/list` | [BETA] Delete projects. |
| POST | `/project/list` | [BETA] Register new projects. Multiple projects for different users can be sent in the same request. |
| PUT | `/project/list` | [BETA] Update multiple projects. |
| GET | `/project/number/{number}` | Find project by number. |
| GET | `/project/orderline` | [BETA] Find all order lines for project. |
| POST | `/project/orderline` | [BETA] Create order line. When creating several order lines, use /list for better performance. |
| POST | `/project/orderline/list` | [BETA] Create multiple order lines. |
| GET | `/project/orderline/orderLineTemplate` | [BETA] Get order line template from project and product |
| GET | `/project/orderline/query` | [BETA] Wildcard search. |
| DELETE | `/project/orderline/{id}` | Delete order line by ID. |
| GET | `/project/orderline/{id}` | [BETA] Get order line by ID. |
| PUT | `/project/orderline/{id}` | [BETA] Update project orderline. |
| POST | `/project/participant` | [BETA] Add new project participant. |
| DELETE | `/project/participant/list` | [BETA] Delete project participants. |
| POST | `/project/participant/list` | [BETA] Add new project participant. Multiple project participants can be sent in the same request. |
| GET | `/project/participant/{id}` | [BETA] Find project participant by ID. |
| PUT | `/project/participant/{id}` | [BETA] Update project participant. |
| POST | `/project/projectActivity` | Add project activity. |
| DELETE | `/project/projectActivity/list` | Delete project activities |
| DELETE | `/project/projectActivity/{id}` | Delete project activity |
| GET | `/project/projectActivity/{id}` | Find project activity by id |
| GET | `/project/resourcePlanBudget` | Get resource plan entries in the specified period. |
| GET | `/project/settings` | Get project settings of logged in company. |
| PUT | `/project/settings` | Update project settings for company |
| GET | `/project/subcontract` | Find project sub-contracts corresponding with sent data. |
| POST | `/project/subcontract` | Add new project sub-contract. |
| GET | `/project/subcontract/query` | Wildcard search. |
| DELETE | `/project/subcontract/{id}` | Delete project sub-contract by ID. |
| GET | `/project/subcontract/{id}` | Find project sub-contract by ID. |
| PUT | `/project/subcontract/{id}` | Update project sub-contract. |
| GET | `/project/task` | Find all tasks for project. |
| GET | `/project/template/{id}` | Get project template by ID. |
| DELETE | `/project/{id}` | [BETA] Delete project. |
| GET | `/project/{id}` | Find project by ID. |
| PUT | `/project/{id}` | [BETA] Update project. |
| GET | `/project/{id}/period/budgetStatus` | Get the budget status for the project period |
| GET | `/project/{id}/period/hourlistReport` | Find hourlist report by project period. |
| GET | `/project/{id}/period/invoiced` | Find invoiced info by project period. |
| GET | `/project/{id}/period/invoicingReserve` | Find invoicing reserve by project period. |
| GET | `/project/{id}/period/monthlyStatus` | Find overall status by project period. |
| GET | `/project/{id}/period/overallStatus` | Find overall status by project period. |
| GET | `/purchaseOrder` | Find purchase orders with send data. Only available for Logistics Basic. |
| POST | `/purchaseOrder` | Creates a new purchase order. Only available for Logistics Basic. |
| GET | `/purchaseOrder/deviation` | Find handled deviations for purchase order. Only available for Logistics Basic. |
| POST | `/purchaseOrder/deviation` | Register deviation on goods receipt. Only available for Logistics Basic. |
| POST | `/purchaseOrder/deviation/list` | Register multiple deviations. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/deviation/list` | Update multiple deviations. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/deviation/{id}` | Delete goods receipt by purchase order ID. Only available for Logistics Basic. |
| GET | `/purchaseOrder/deviation/{id}` | Get deviation by order line ID. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/deviation/{id}` | Update deviation. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/deviation/{id}/:approve` | Approve deviations. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/deviation/{id}/:deliver` | Send deviations to approval. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/deviation/{id}/:undeliver` | Set status to Not delivered for deviations. Only available for Logistics Basic. |
| GET | `/purchaseOrder/goodsReceipt` | Get goods receipt. Only available for Logistics Basic. |
| POST | `/purchaseOrder/goodsReceipt` | Register goods receipt without an existing purchase order. When registration of several goods receipt, use /list for better performance. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/goodsReceipt/list` | Delete multiple goods receipts by ID. Only available for Logistics Basic. |
| POST | `/purchaseOrder/goodsReceipt/list` | Register multiple goods receipts without an existing purchase order. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/goodsReceipt/{id}` | Delete goods receipt by ID. Only available for Logistics Basic. |
| GET | `/purchaseOrder/goodsReceipt/{id}` | Get goods receipt by purchase order ID. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/goodsReceipt/{id}` | Update goods receipt. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/goodsReceipt/{id}/:confirm` | Confirm goods receipt. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/goodsReceipt/{id}/:receiveAndConfirm` | Receive all ordered products and approve goods receipt. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/goodsReceipt/{id}/:registerGoodsReceipt` | Register goods receipt. Quantity received on the products is set to the same as quantity ordered. To update the quantity received, use PUT /purchaseOrder/goodsReceiptLine/{id}. Only available for L... |
| GET | `/purchaseOrder/goodsReceiptLine` | Find goods receipt lines for purchase order. Only available for Logistics Basic. |
| POST | `/purchaseOrder/goodsReceiptLine` | Register new goods receipt; new product on an existing purchase order. When registration of several goods receipts, use /list for better performance. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/goodsReceiptLine/list` | Delete goods receipt lines by ID. Only available for Logistics Basic. |
| POST | `/purchaseOrder/goodsReceiptLine/list` | Register multiple new goods receipts on an existing purchase order. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/goodsReceiptLine/list` | Update goods receipt lines on a goods receipt. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/goodsReceiptLine/{id}` | Delete goods receipt line by ID. Only available for Logistics Basic. |
| GET | `/purchaseOrder/goodsReceiptLine/{id}` | Get goods receipt line by purchase order line ID. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/goodsReceiptLine/{id}` | Update a goods receipt line on a goods receipt. Only available for Logistics Basic. |
| POST | `/purchaseOrder/orderline` | Creates purchase order line. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/orderline/list` | Delete purchase order lines by ID. Only available for Logistics Basic. |
| POST | `/purchaseOrder/orderline/list` | Create list of new purchase order lines. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/orderline/list` | Update a list of purchase order lines. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/orderline/{id}` | Delete purchase order line. Only available for Logistics Basic. |
| GET | `/purchaseOrder/orderline/{id}` | Find purchase order line by ID. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/orderline/{id}` | Updates purchase order line. Only available for Logistics Basic. |
| GET | `/purchaseOrder/purchaseOrderIncomingInvoiceRelation` | Find purchase order relation to voucher with sent data. Only available for Logistics Basic. |
| POST | `/purchaseOrder/purchaseOrderIncomingInvoiceRelation` | Create new relation between purchase order and a voucher. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/purchaseOrderIncomingInvoiceRelation/list` | Delete multiple purchase order voucher relations. Only available for Logistics Basic. |
| POST | `/purchaseOrder/purchaseOrderIncomingInvoiceRelation/list` | Create a new list of relations between purchase order and voucher. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/purchaseOrderIncomingInvoiceRelation/{id}` | Delete purchase order voucher relation. Only available for Logistics Basic. |
| GET | `/purchaseOrder/purchaseOrderIncomingInvoiceRelation/{id}` | Find purchase order relation to voucher by ID. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/{id}` | Delete purchase order. Only available for Logistics Basic. |
| GET | `/purchaseOrder/{id}` | Find purchase order by ID. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/{id}` | Update purchase order. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/{id}/:send` | Send purchase order by ID and sendType. Only available for Logistics Basic. |
| PUT | `/purchaseOrder/{id}/:sendByEmail` | Send purchase order by customisable email. Only available for Logistics Basic. |
| DELETE | `/purchaseOrder/{id}/attachment` | Delete attachment. Only available for Logistics Basic. |
| POST | `/purchaseOrder/{id}/attachment` | Upload attachment to purchase order. Only available for Logistics Basic. |
| POST | `/purchaseOrder/{id}/attachment/list` | Upload multiple attachments to Purchase Order. Only available for Logistics Basic. |
| GET | `/reminder` | Find reminders corresponding with sent data. |
| GET | `/reminder/{id}` | Get reminder by ID. |
| GET | `/reminder/{reminderId}/pdf` | Get reminder document by reminder ID. |
| GET | `/resultbudget` | Find result budgets corresponding with sent data. Either specify the ids of the departments, projects, products or employees to return result budgets for, or use the boolean parameters includeAll**... |
| GET | `/resultbudget/company` | Get result budget for company |
| GET | `/resultbudget/department/{id}` | Get result budget associated with a departmentId |
| GET | `/resultbudget/employee/{id}` | Get result budget associated with an employeeId |
| GET | `/resultbudget/product/{id}` | Get result budget associated with a productId |
| GET | `/resultbudget/project/{id}` | Get result budget associated with a projectId |
| GET | `/saft/exportSAFT` | [BETA] Create SAF-T export for the Tripletex account. |
| POST | `/saft/importSAFT` | [BETA] Import SAF-T. Send XML file as multipart form. |
| GET | `/salary/compilation` | Find salary compilation by employee. |
| GET | `/salary/compilation/pdf` | Find salary compilation (PDF document) by employee. |
| POST | `/salary/financeTax/reconciliation/context` | Create a financeTax reconciliation context for a customer |
| GET | `/salary/financeTax/reconciliation/{reconciliationId}/overview` | Get finance tax overview for a specific reconciliation term |
| GET | `/salary/financeTax/reconciliation/{reconciliationId}/paymentsOverview` | Get finance tax payment overview from start of year to the current reconciliation term |
| POST | `/salary/holidayAllowance/reconciliation/context` | Create a holiday allowance reconciliation context for a customer |
| GET | `/salary/holidayAllowance/reconciliation/{reconciliationId}/holidayAllowanceDetails` | Get a holiday allowance details for the current reconciliation term |
| GET | `/salary/holidayAllowance/reconciliation/{reconciliationId}/holidayAllowanceSummary` | Salary holiday allowance reconciliation summary |
| POST | `/salary/mandatoryDeduction/reconciliation/context` | Create a mandatoryDeduction reconciliation context for a customer |
| GET | `/salary/mandatoryDeduction/reconciliation/{reconciliationId}/overview` | Salary mandatory deduction reconciliation overview |
| GET | `/salary/mandatoryDeduction/reconciliation/{reconciliationId}/paymentsOverview` | Get mandatory deduction payments overview from start of year to the current reconciliation term |
| POST | `/salary/payrollTax/reconciliation/context` | Create a payroll tax reconciliation context for a customer |
| GET | `/salary/payrollTax/reconciliation/{reconciliationId}/overview` | Salary payroll tax reconciliation overview |
| GET | `/salary/payrollTax/reconciliation/{reconciliationId}/paymentsOverview` | Get a payroll tax payments from start of year to the current reconciliation term |
| GET | `/salary/payslip` | Find payslips corresponding with sent data. |
| GET | `/salary/payslip/{id}` | Find payslip by ID. |
| GET | `/salary/payslip/{id}/pdf` | Find payslip (PDF document) by ID. |
| GET | `/salary/settings` | Get salary settings of logged in company. |
| PUT | `/salary/settings` | Update settings of logged in company. |
| GET | `/salary/settings/holiday` | Find holiday settings of current logged in company. |
| POST | `/salary/settings/holiday` | Create a holiday setting of current logged in company. |
| DELETE | `/salary/settings/holiday/list` | Delete multiple holiday settings of current logged in company. |
| POST | `/salary/settings/holiday/list` | Create multiple holiday settings of current logged in company. |
| PUT | `/salary/settings/holiday/list` | Update multiple holiday settings of current logged in company. |
| PUT | `/salary/settings/holiday/{id}` | Update a holiday setting of current logged in company. |
| GET | `/salary/settings/pensionScheme` | Find pension schemes. |
| POST | `/salary/settings/pensionScheme` | Create a Pension Scheme. |
| DELETE | `/salary/settings/pensionScheme/list` | Delete multiple Pension Schemes. |
| POST | `/salary/settings/pensionScheme/list` | Create multiple Pension Schemes. |
| PUT | `/salary/settings/pensionScheme/list` | Update multiple Pension Schemes. |
| DELETE | `/salary/settings/pensionScheme/{id}` | Delete a Pension Scheme |
| GET | `/salary/settings/pensionScheme/{id}` | Get Pension Scheme for a specific ID |
| PUT | `/salary/settings/pensionScheme/{id}` | Update a Pension Scheme |
| GET | `/salary/settings/standardTime` | Get all standard times. |
| POST | `/salary/settings/standardTime` | Create standard time. |
| GET | `/salary/settings/standardTime/byDate` | Find standard time by date |
| GET | `/salary/settings/standardTime/{id}` | Find standard time by ID. |
| PUT | `/salary/settings/standardTime/{id}` | Update standard time. |
| POST | `/salary/taxDeduction/reconciliation/context` | Create a taxDeduction reconciliation context for a customer |
| GET | `/salary/taxDeduction/reconciliation/{reconciliationId}/balanceAndOwedAmount` | Get tax deduction details for a reconciliation |
| GET | `/salary/taxDeduction/reconciliation/{reconciliationId}/overview` | Get salary tax deduction data for the reconciliation table |
| GET | `/salary/taxDeduction/reconciliation/{reconciliationId}/paymentsOverview` | Get salary tax deduction payment overview from start of year to the current reconciliation term |
| POST | `/salary/transaction` | Create a new salary transaction. |
| DELETE | `/salary/transaction/{id}` | Delete salary transaction by ID. |
| GET | `/salary/transaction/{id}` | Find salary transaction by ID. |
| POST | `/salary/transaction/{id}/attachment` | Upload an attachment to a salary transaction |
| POST | `/salary/transaction/{id}/attachment/list` | Upload multiple attachments to a salary transaction |
| PUT | `/salary/transaction/{id}/deleteAttachment` | Delete attachment. |
| GET | `/salary/type` | Find salary type corresponding with sent data. |
| GET | `/salary/type/{id}` | Find salary type by ID. |
| PUT | `/subscription/cancel` | Close account with/without read access |
| GET | `/subscription/packages` | Returns the packages that can exist for an account. |
| PUT | `/subscription/reactivate` | Reopen account with previous modules |
| GET | `/supplier` | Find suppliers corresponding with sent data. |
| POST | `/supplier` | Create supplier. Related supplier addresses may also be created. |
| POST | `/supplier/list` | Create multiple suppliers. Related supplier addresses may also be created. |
| PUT | `/supplier/list` | Update multiple suppliers. Addresses can also be updated. |
| DELETE | `/supplier/{id}` | Delete supplier by ID |
| GET | `/supplier/{id}` | Get supplier by ID. |
| PUT | `/supplier/{id}` | Update supplier. |
| GET | `/supplierCustomer/search` | Find all active suppliers and customers. |
| GET | `/supplierInvoice` | Find supplierInvoices corresponding with sent data. |
| PUT | `/supplierInvoice/:addRecipient` | Add recipient. |
| PUT | `/supplierInvoice/:approve` | Approve supplier invoices. |
| PUT | `/supplierInvoice/:reject` | reject supplier invoices. |
| GET | `/supplierInvoice/forApproval` | Get supplierInvoices for approval |
| PUT | `/supplierInvoice/voucher/{id}/postings` | [BETA] Put debit postings. |
| GET | `/supplierInvoice/{id}` | Get supplierInvoice by ID. |
| POST | `/supplierInvoice/{invoiceId}/:addPayment` | Register payment, paymentType == 0 finds the last paymentType for this vendor.Use of this method requires setup done by Tripletex. |
| PUT | `/supplierInvoice/{invoiceId}/:addRecipient` | Add recipient to supplier invoices. |
| PUT | `/supplierInvoice/{invoiceId}/:approve` | Approve supplier invoice. |
| PUT | `/supplierInvoice/{invoiceId}/:changeDimension` | Change dimension on a supplier invoice. |
| PUT | `/supplierInvoice/{invoiceId}/:reject` | reject supplier invoice. |
| GET | `/supplierInvoice/{invoiceId}/pdf` | Get supplierInvoice document by invoice ID. |
| GET | `/supportDashboard/bankruptAndExcludedCustomers` | Returns the customers for support dashboard. |
| GET | `/supportDashboard/export` | Export the customers table to a specific format |
| GET | `/timesheet/allocated` | Find allocated hour entries corresponding with sent data. |
| POST | `/timesheet/allocated` | Add new allocated hour entry. Only one entry per employee/date/activity/project combination is supported. Only holiday/vacation hours can receive comments. A notification will be sent to the entry'... |
| PUT | `/timesheet/allocated/:approveList` | Only for allocated hours on the company's internal holiday/vacation activity. Mark the allocated hour entry/entries as approved. The hours will be copied to the time sheet if the relevant weeks/mon... |
| PUT | `/timesheet/allocated/:unapproveList` | Only for allocated hours on the company's internal holiday/vacation activity. Mark the allocated hour entry/entries as unapproved. Notifications will be sent to the entries' employees if the entrie... |
| POST | `/timesheet/allocated/list` | Add new allocated hour entry. Multiple objects for several users can be sent in the same request. Only holiday/vacation hours can receive comments. Notifications will be sent to the entries' employ... |
| PUT | `/timesheet/allocated/list` | Update allocated hour entry. Multiple objects for different users can be sent in the same request. Note: Allocated hour entry object fields which are present but not set, or set to 0, will be nulle... |
| DELETE | `/timesheet/allocated/{id}` | Delete allocated hour entry by ID. |
| GET | `/timesheet/allocated/{id}` | Find allocated hour entry by ID. |
| PUT | `/timesheet/allocated/{id}` | Update allocated hour entry by ID. Note: Allocated hour entry object fields which are present but not set, or set to 0, will be nulled. Only holiday/vacation hours can receive comments. A notificat... |
| PUT | `/timesheet/allocated/{id}/:approve` | Only for allocated hours on the company's internal holiday/vacation activity. Mark the allocated hour entry as approved. The hours will be copied to the time sheet if the relevant week/month is not... |
| PUT | `/timesheet/allocated/{id}/:unapprove` | Only for allocated hours on the company's internal holiday/vacation activity. Mark the allocated hour entry as unapproved. A notification will be sent to the entry's employee if the entry's approva... |
| GET | `/timesheet/companyHoliday` | [BETA] Search for company holidays by id or year. |
| POST | `/timesheet/companyHoliday` | [BETA] Create a company holiday |
| DELETE | `/timesheet/companyHoliday/{id}` | [BETA] Delete a company holiday |
| GET | `/timesheet/companyHoliday/{id}` | [BETA] Get company holiday by its ID |
| PUT | `/timesheet/companyHoliday/{id}` | [BETA] Update a company holiday |
| GET | `/timesheet/entry` | Find timesheet entry corresponding with sent data. |
| POST | `/timesheet/entry` | Add new timesheet entry. Only one entry per employee/date/activity/project combination is supported. |
| GET | `/timesheet/entry/>recentActivities` | Find recently used timesheet activities. |
| GET | `/timesheet/entry/>recentProjects` | Find projects with recent activities (timesheet entry registered). |
| GET | `/timesheet/entry/>totalHours` | Find total hours registered on an employee in a specific period. |
| POST | `/timesheet/entry/list` | Add new timesheet entry. Multiple objects for several users can be sent in the same request. |
| PUT | `/timesheet/entry/list` | Update timesheet entry. Multiple objects for different users can be sent in the same request. |
| DELETE | `/timesheet/entry/{id}` | Delete timesheet entry by ID. |
| GET | `/timesheet/entry/{id}` | Find timesheet entry by ID. |
| PUT | `/timesheet/entry/{id}` | Update timesheet entry by ID. Note: Timesheet entry object fields which are present but not set, or set to 0, will be nulled. |
| PUT | `/timesheet/month/:approve` | approve month(s).  If id is provided the other args are ignored |
| PUT | `/timesheet/month/:complete` | complete month(s).  If id is provided the other args are ignored |
| PUT | `/timesheet/month/:reopen` | reopen month(s).  If id is provided the other args are ignored |
| PUT | `/timesheet/month/:unapprove` | unapprove month(s).  If id is provided the other args are ignored |
| GET | `/timesheet/month/byMonthNumber` | Find monthly status for given month. |
| GET | `/timesheet/month/byMonthNumberList` | Find monthly status for given month list. |
| GET | `/timesheet/month/{id}` | Find monthly status entry by ID. |
| GET | `/timesheet/salaryProjectTypeSpecification` | Get list of time sheet ProjectSalaryType specifications |
| POST | `/timesheet/salaryProjectTypeSpecification` | Create a timesheet ProjectSalaryType specification |
| DELETE | `/timesheet/salaryProjectTypeSpecification/{id}` | Delete a timesheet SalaryType specification |
| GET | `/timesheet/salaryProjectTypeSpecification/{id}` | Get timesheet ProjectSalaryType specification for a specific ID |
| PUT | `/timesheet/salaryProjectTypeSpecification/{id}` | Update a timesheet ProjectSalaryType specification |
| GET | `/timesheet/salaryTypeSpecification` | [BETA] Get list of timesheet SalaryType Specifications |
| POST | `/timesheet/salaryTypeSpecification` | [BETA] Create a timesheet SalaryType Specification. Only one entry per employee/date/SalaryType |
| DELETE | `/timesheet/salaryTypeSpecification/{id}` | [BETA] Delete a timesheet SalaryType Specification |
| GET | `/timesheet/salaryTypeSpecification/{id}` | [BETA] Get timesheet SalaryType Specification for a specific ID |
| PUT | `/timesheet/salaryTypeSpecification/{id}` | [BETA] Update a timesheet SalaryType Specification |
| GET | `/timesheet/settings` | [BETA] Get timesheet settings of logged in company. |
| GET | `/timesheet/timeClock` | Find time clock entries corresponding with sent data. |
| PUT | `/timesheet/timeClock/:start` | Start time clock. |
| GET | `/timesheet/timeClock/present` | Find a user’s present running time clock. |
| GET | `/timesheet/timeClock/{id}` | Find time clock entry by ID. |
| PUT | `/timesheet/timeClock/{id}` | Update time clock by ID. |
| PUT | `/timesheet/timeClock/{id}/:stop` | Stop time clock. |
| GET | `/timesheet/week` | Find weekly status By ID, week/year combination, employeeId or an approver |
| PUT | `/timesheet/week/:approve` | Approve week. By ID or (ISO-8601 week and employeeId combination). |
| PUT | `/timesheet/week/:complete` | Complete week. By ID or (ISO-8601 week and employeeId combination). |
| PUT | `/timesheet/week/:reopen` | Reopen week. By ID or (ISO-8601 week and employeeId combination). |
| PUT | `/timesheet/week/:unapprove` | Unapprove week. By ID or (ISO-8601 week and employeeId combination). |
| GET | `/token/consumer/byToken` | Get consumer token by token string. |
| PUT | `/token/employee/:create` | Create an employee token. Only selected consumers are allowed |
| POST | `/token/session/:create` | Create session token. |
| PUT | `/token/session/:create` | Create session token. |
| GET | `/token/session/>whoAmI` | Find information about the current user. |
| DELETE | `/token/session/{token}` | Delete session token. |
| GET | `/transportType` | [BETA] Search transport type by supplier. |
| GET | `/transportType/{id}` | [BETA] Find transport type by ID. |
| GET | `/travelExpense` | Find travel expenses corresponding with sent data. |
| POST | `/travelExpense` | Create travel expense. |
| PUT | `/travelExpense/:approve` | Approve travel expenses. |
| PUT | `/travelExpense/:copy` | Copy travel expense. |
| PUT | `/travelExpense/:createVouchers` | Create vouchers |
| PUT | `/travelExpense/:deliver` | Deliver travel expenses. |
| PUT | `/travelExpense/:unapprove` | Unapprove travel expenses. |
| PUT | `/travelExpense/:undeliver` | Undeliver travel expenses. |
| GET | `/travelExpense/accommodationAllowance` | Find accommodation allowances corresponding with sent data. |
| POST | `/travelExpense/accommodationAllowance` | Create accommodation allowance. |
| DELETE | `/travelExpense/accommodationAllowance/{id}` | Delete accommodation allowance. |
| GET | `/travelExpense/accommodationAllowance/{id}` | Get travel accommodation allowance by ID. |
| PUT | `/travelExpense/accommodationAllowance/{id}` | Update accommodation allowance. |
| GET | `/travelExpense/cost` | Find costs corresponding with sent data. |
| POST | `/travelExpense/cost` | Create cost. |
| PUT | `/travelExpense/cost/list` | Update costs. |
| DELETE | `/travelExpense/cost/{id}` | Delete cost. |
| GET | `/travelExpense/cost/{id}` | Get cost by ID. |
| PUT | `/travelExpense/cost/{id}` | Update cost. |
| GET | `/travelExpense/costCategory` | Find cost category corresponding with sent data. |
| GET | `/travelExpense/costCategory/{id}` | Get cost category by ID. |
| POST | `/travelExpense/costParticipant` | Create participant on cost. |
| POST | `/travelExpense/costParticipant/createCostParticipantAdvanced` | Create participant on cost using explicit parameters |
| DELETE | `/travelExpense/costParticipant/list` | Delete cost participants. |
| POST | `/travelExpense/costParticipant/list` | Create participants on cost. |
| GET | `/travelExpense/costParticipant/{costId}/costParticipants` | Get cost's participants by costId. |
| DELETE | `/travelExpense/costParticipant/{id}` | Delete cost participant. |
| GET | `/travelExpense/costParticipant/{id}` | Get cost participant by ID. |
| POST | `/travelExpense/drivingStop` | Create mileage allowance driving stop. |
| DELETE | `/travelExpense/drivingStop/{id}` | Delete mileage allowance stops. |
| GET | `/travelExpense/drivingStop/{id}` | Get driving stop by ID. |
| GET | `/travelExpense/mileageAllowance` | Find mileage allowances corresponding with sent data. |
| POST | `/travelExpense/mileageAllowance` | Create mileage allowance. |
| DELETE | `/travelExpense/mileageAllowance/{id}` | Delete mileage allowance. |
| GET | `/travelExpense/mileageAllowance/{id}` | Get mileage allowance by ID. |
| PUT | `/travelExpense/mileageAllowance/{id}` | Update mileage allowance. |
| GET | `/travelExpense/passenger` | Find passengers corresponding with sent data. |
| POST | `/travelExpense/passenger` | Create passenger. |
| DELETE | `/travelExpense/passenger/list` | Delete passengers. |
| POST | `/travelExpense/passenger/list` | Create passengers. |
| DELETE | `/travelExpense/passenger/{id}` | Delete passenger. |
| GET | `/travelExpense/passenger/{id}` | Get passenger by ID. |
| PUT | `/travelExpense/passenger/{id}` | Update passenger. |
| GET | `/travelExpense/paymentType` | Find payment type corresponding with sent data. |
| GET | `/travelExpense/paymentType/{id}` | Get payment type by ID. |
| GET | `/travelExpense/perDiemCompensation` | Find per diem compensations corresponding with sent data. |
| POST | `/travelExpense/perDiemCompensation` | Create per diem compensation. |
| DELETE | `/travelExpense/perDiemCompensation/{id}` | Delete per diem compensation. |
| GET | `/travelExpense/perDiemCompensation/{id}` | Get per diem compensation by ID. |
| PUT | `/travelExpense/perDiemCompensation/{id}` | Update per diem compensation. |
| GET | `/travelExpense/rate` | Find rates corresponding with sent data. |
| GET | `/travelExpense/rate/{id}` | Get travel expense rate by ID. |
| GET | `/travelExpense/rateCategory` | Find rate categories corresponding with sent data. |
| GET | `/travelExpense/rateCategory/{id}` | Get travel expense rate category by ID. |
| GET | `/travelExpense/rateCategoryGroup` | Find rate categoriy groups corresponding with sent data. |
| GET | `/travelExpense/rateCategoryGroup/{id}` | Get travel report rate category group by ID. |
| GET | `/travelExpense/settings` | Get travel expense settings of logged in company. |
| GET | `/travelExpense/zone` | Find travel expense zones corresponding with sent data. |
| GET | `/travelExpense/zone/{id}` | Get travel expense zone by ID. |
| DELETE | `/travelExpense/{id}` | Delete travel expense. |
| GET | `/travelExpense/{id}` | Get travel expense by ID. |
| PUT | `/travelExpense/{id}` | Update travel expense. |
| PUT | `/travelExpense/{id}/convert` | Convert travel to/from employee expense. |
| DELETE | `/travelExpense/{travelExpenseId}/attachment` | Delete attachment. |
| GET | `/travelExpense/{travelExpenseId}/attachment` | Get attachment by travel expense ID. |
| POST | `/travelExpense/{travelExpenseId}/attachment` | Upload attachment to travel expense. |
| POST | `/travelExpense/{travelExpenseId}/attachment/list` | Upload multiple attachments to travel expense. |
| POST | `/userLicense/export` | Export the user licenses table to a specific format |
| GET | `/vatReturns/comment` | [BETA] - Get all structured comments related to a given vatCode |
| GET | `/vatReturns/comment/>all` | [BETA] - Get all structured comments available |
| GET | `/vatTermSizeSettings` | Search for VatTermSizeSettings |
| POST | `/vatTermSizeSettings` | Create VatTermSizeSettings |
| DELETE | `/vatTermSizeSettings/{id}` | Delete VatTermSizeSettings |
| GET | `/vatTermSizeSettings/{id}` | Get VatTermSizeSettings by ID. VatTermSizeSettings is used to define VAT term lengths. |
| PUT | `/vatTermSizeSettings/{id}` | Update VatTermSizeSettings. |
| GET | `/voucherApprovalListElement/{id}` | Get by ID. |
| GET | `/voucherInbox/inboxCount` | Get count of items in the Voucher Inbox |
| GET | `/voucherMessage` | [BETA] Find voucherMessage (or a comment) put on a voucher by inputting voucher ids |
| POST | `/voucherMessage` | [BETA] Post new voucherMessage. |
| GET | `/voucherStatus` | Find voucherStatus corresponding with sent data. The voucherStatus is used to coordinate integration processes. Requires setup done by Tripletex, currently supports debt collection. |
| POST | `/voucherStatus` | Post new voucherStatus. |
| GET | `/voucherStatus/{id}` | Get voucherStatus by ID. |
| GET | `/yearEnd/enumType/businessActivityTypes` | Get business activity types |
| GET | `/yearEnd/penneo/casefiles` | Get case files from Penneo for a specific year |
| POST | `/yearEnd/penneo/casefiles` | Create a new case file in Penneo |
| DELETE | `/yearEnd/penneo/casefiles/{caseFileId}` | Delete a case file from Penneo |
| POST | `/yearEnd/penneo/casefiles/{caseFileId}/activate` | Fully activate a case file for signing (links signers, configures emails, and activates) |
| DELETE | `/yearEnd/penneo/casefiles/{caseFileId}/signers/{signerId}` | Delete a signer from a case file |
| POST | `/yearEnd/penneo/casefiles/{caseFileId}/signers/{signerId}/reactivate` | Reactivate a signer in a case file |
| POST | `/yearEnd/penneo/casefiles/{caseFileId}/signers/{signerId}/resend` | Resend a sign link to a specific signer |
| POST | `/yearEnd/penneo/documents` | Add a document to an existing case file |
| DELETE | `/yearEnd/penneo/documents/{documentId}` | Delete a document from a case file |
| PUT | `/yearEnd/penneo/documents/{documentId}` | Update an existing document in a case file |
| GET | `/yearEnd/penneo/documents/{documentId}/download` | Download a document from Penneo |
| GET | `/yearEnd/penneo/recipients` | Get all recipients for a case file |
| POST | `/yearEnd/penneo/recipients` | Add a copy recipient to a case file |
| DELETE | `/yearEnd/penneo/recipients/{id}` | Delete a recipient from a case file |
| GET | `/yearEnd/penneo/session` | Authenticate and get case files from Penneo for a specific year |
| POST | `/yearEnd/penneo/signature-lines` | Create signature line, link signer, and configure email in one operation |
| POST | `/yearEnd/penneo/sync` | Synchronize database with current Penneo casefile state |
| POST | `/yearEnd/penneo/updateCompletedStatus` | Update completed status for current company's casefiles from global API |
| DELETE | `/yearEnd/researchAndDevelopment2024` | Delete ResearchAndDevelopment 2024 |
| POST | `/yearEnd/researchAndDevelopment2024` | Create ResearchAndDevelopment 2024 |
| PUT | `/yearEnd/researchAndDevelopment2024` | Update ResearchAndDevelopment 2024 |
| GET | `/yearEnd/{yearEndReportId}/researchAndDevelopment2024` | Get ResearchAndDevelopment by corresponding data 2024 |
