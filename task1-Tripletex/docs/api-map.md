# Tripletex API Map — Competition-Relevant Endpoints

## contact (3 endpoints)

- `GET, POST` **/contact** — Find contacts corresponding with sent data.
- `POST, DELETE` **/contact/list** — Create multiple contacts.
- `GET, PUT` **/contact/{id}** — Get contact by ID.

## country (2 endpoints)

- `GET` **/country** — Find countries corresponding with sent data.
- `GET` **/country/{id}** — Get country by ID.

## currency (5 endpoints)

- `GET` **/currency** — Find currencies corresponding with sent data.
- `GET` **/currency/{fromCurrencyID}/exchangeRate** — Returns the amount in the company currency, where the input amount is in fromCurrency, using the newest exchange rate available for the given date
- `GET` **/currency/{fromCurrencyID}/{toCurrencyID}/exchangeRate** — Returns the amount in the specified currency, where the input amount is in fromCurrency, using the newest exchange rate available for the given date
- `GET` **/currency/{id}** — Get currency by ID.
- `GET` **/currency/{id}/rate** — Find currency exchange rate corresponding with sent data.

## customer (5 endpoints)

- `GET, POST` **/customer** — Find customers corresponding with sent data.
- `GET, POST` **/customer/category** — Find customer/supplier categories corresponding with sent data.
- `GET, PUT` **/customer/category/{id}** — Find customer/supplier category by ID.
- `PUT, POST` **/customer/list** — [BETA] Update multiple customers. Addresses can also be updated.
- `GET, PUT, DELETE` **/customer/{id}** — Get customer by ID.

## deliveryAddress (2 endpoints)

- `GET` **/deliveryAddress** — Find addresses corresponding with sent data.
- `GET, PUT` **/deliveryAddress/{id}** — Get address by ID.

## department (4 endpoints)

- `GET, POST` **/department** — Find department corresponding with sent data.
- `PUT, POST` **/department/list** — Update multiple departments.
- `GET` **/department/query** — Wildcard search.
- `GET, PUT, DELETE` **/department/{id}** — Get department by ID.

## employee (42 endpoints)

- `GET, POST` **/employee** — Find employees corresponding with sent data.
- `GET, POST` **/employee/category** — Find employee category corresponding with sent data.
- `PUT, POST, DELETE` **/employee/category/list** — Update multiple employee categories.
- `GET, PUT, DELETE` **/employee/category/{id}** — Get employee category by ID.
- `GET, POST` **/employee/employment** — Find all employments for employee.
- `GET, POST` **/employee/employment/details** — Find all employmentdetails for employment.
- `GET, PUT` **/employee/employment/details/{id}** — Find employment details by ID.
- `GET` **/employee/employment/employmentType** — Find all employment type IDs.
- `GET` **/employee/employment/employmentType/employmentEndReasonType** — Find all employment end reason type IDs.
- `GET` **/employee/employment/employmentType/employmentFormType** — Find all employment form type IDs.
- `GET` **/employee/employment/employmentType/maritimeEmploymentType** — Find all maritime employment type IDs.
- `GET` **/employee/employment/employmentType/salaryType** — Find all salary type IDs.
- `GET` **/employee/employment/employmentType/scheduleType** — Find all schedule type IDs.
- `GET, POST` **/employee/employment/leaveOfAbsence** — Find all leave of absence corresponding with the sent data.
- `POST` **/employee/employment/leaveOfAbsence/list** — Create multiple leave of absences.
- `GET, PUT` **/employee/employment/leaveOfAbsence/{id}** — Find leave of absence by ID.
- `GET` **/employee/employment/leaveOfAbsenceType** — Find all leave of absence type IDs.
- `GET` **/employee/employment/occupationCode** — Find all profession codes.
- `GET` **/employee/employment/occupationCode/{id}** — Get occupation by ID.
- `GET` **/employee/employment/remunerationType** — Find all remuneration type IDs.
- `GET` **/employee/employment/workingHoursScheme** — Find working hours scheme ID.
- `GET, PUT` **/employee/employment/{id}** — Find employment by ID.
- `GET` **/employee/entitlement** — Find all entitlements for user.
- `PUT` **/employee/entitlement/:grantClientEntitlementsByTemplate** — [BETA] Update employee entitlements in client account.
- `PUT` **/employee/entitlement/:grantEntitlementsByTemplate** — [BETA] Update employee entitlements.
- `GET` **/employee/entitlement/client** — [BETA] Find all entitlements at client for user.
- `GET` **/employee/entitlement/{id}** — Get entitlement by ID.
- `GET, POST` **/employee/hourlyCostAndRate** — Find all hourly cost and rates for employee.
- `GET, PUT` **/employee/hourlyCostAndRate/{id}** — Find hourly cost and rate by ID.
- `POST` **/employee/list** — Create several employees.
- `GET, POST` **/employee/nextOfKin** — Find all next of kin for employee.
- `GET, PUT` **/employee/nextOfKin/{id}** — Find next of kin by ID.
- `GET` **/employee/preferences** — Find employee preferences corresponding with sent data.
- `PUT` **/employee/preferences/:changeLanguage** — Change current employees language to the given language
- `GET` **/employee/preferences/>loggedInEmployeePreferences** — Get employee preferences for current user
- `PUT` **/employee/preferences/list** — Update multiple employee preferences.
- `PUT` **/employee/preferences/{id}** — Update employee preferences information.
- `GET` **/employee/searchForEmployeesAndContacts** — Get employees and contacts by parameters. Include contacts by default.
- `GET, POST` **/employee/standardTime** — Find all standard times for employee.
- `GET` **/employee/standardTime/byDate** — Find standard time for employee by date.
- `GET, PUT` **/employee/standardTime/{id}** — Find standard time by ID.
- `GET, PUT` **/employee/{id}** — Get employee by ID.

## invoice (12 endpoints)

- `GET, POST` **/invoice** — Find invoices corresponding with sent data. Includes charged outgoing invoices only.
- `GET` **/invoice/details** — Find ProjectInvoiceDetails corresponding with sent data.
- `GET` **/invoice/details/{id}** — Get ProjectInvoiceDetails by ID.
- `POST` **/invoice/list** — [BETA] Create multiple invoices. Max 100 at a time.
- `GET` **/invoice/paymentType** — Find payment type corresponding with sent data.
- `GET` **/invoice/paymentType/{id}** — Get payment type by ID.
- `GET` **/invoice/{id}** — Get invoice by ID.
- `PUT` **/invoice/{id}/:createCreditNote** — Creates a new Invoice representing a credit memo that nullifies the given invoice. Updates this invoice and any pre-existing inverse invoice.
- `PUT` **/invoice/{id}/:createReminder** — Create invoice reminder and sends it by the given dispatch type. Supports the reminder types SOFT_REMINDER, REMINDER and NOTICE_OF_DEBT_COLLECTION. DispatchType NETS_PRINT must have type NOTICE_OF_DEBT_COLLECTION. SMS and NETS_PRINT must be activated prior to usage in the API.
- `PUT` **/invoice/{id}/:payment** — Update invoice. The invoice is updated with payment information. The amount is in the invoice’s currency.
- `PUT` **/invoice/{id}/:send** — Send invoice by ID and sendType. Optionally override email recipient.
- `GET` **/invoice/{invoiceId}/pdf** — Get invoice document by invoice ID.

## ledger (55 endpoints)

- `GET` **/ledger** — Get ledger (hovedbok).
- `GET, POST` **/ledger/account** — Find accounts corresponding with sent data.
- `PUT, POST, DELETE` **/ledger/account/list** — Update multiple accounts.
- `GET, PUT, DELETE` **/ledger/account/{id}** — Get account by ID.
- `GET, POST` **/ledger/accountingDimensionName** — Get all accounting dimension names.
- `GET` **/ledger/accountingDimensionName/search** — Search for accounting dimension names according to criteria.
- `GET, PUT, DELETE` **/ledger/accountingDimensionName/{id}** — Get a single accounting dimension name by ID
- `POST` **/ledger/accountingDimensionValue** — Create a new value for one of the free (aka 'user defined') accounting dimensions
- `PUT` **/ledger/accountingDimensionValue/list** — Update accounting dimension values
- `GET` **/ledger/accountingDimensionValue/search** — Search for accounting dimension values according to criteria.
- `GET, DELETE` **/ledger/accountingDimensionValue/{id}** — Find accounting dimension values by ID.
- `GET` **/ledger/accountingPeriod** — Find accounting periods corresponding with sent data.
- `GET` **/ledger/accountingPeriod/{id}** — Get accounting period by ID.
- `GET` **/ledger/annualAccount** — Find annual accounts corresponding with sent data.
- `GET` **/ledger/annualAccount/{id}** — Get annual account by ID.
- `GET` **/ledger/closeGroup** — Find close groups corresponding with sent data.
- `GET` **/ledger/closeGroup/{id}** — Get close group by ID.
- `GET` **/ledger/openPost** — Find open posts corresponding with sent data.
- `GET, POST` **/ledger/paymentTypeOut** — [BETA] Gets payment types for outgoing payments
- `PUT, POST` **/ledger/paymentTypeOut/list** — [BETA] Update multiple payment types for outgoing payments at once
- `GET, PUT, DELETE` **/ledger/paymentTypeOut/{id}** — [BETA] Get payment type for outgoing payments by ID.
- `GET` **/ledger/posting** — Find postings corresponding with sent data.
- `PUT` **/ledger/posting/:closePostings** — Close postings.
- `GET` **/ledger/posting/openPost** — Find open posts corresponding with sent data.
- `GET` **/ledger/posting/{id}** — Find postings by ID.
- `GET` **/ledger/postingByDate** — Get postings by date range with pagination. Returns the same PostingDTO as /ledger/posting. Simplified endpoint for better performance. Fields and Changes are not supported. Token must have access to all vouchers in the company, otherwise a validation error is returned. If access control for salary information is activated, the token must have access to salary information as well.
- `GET` **/ledger/postingRules** — Get posting rules for current company.  The posting rules defined which accounts from the chart of accounts that are used for postings when the system creates postings.
- `GET, PUT` **/ledger/vatSettings** — Get VAT settings for the logged in company.
- `GET` **/ledger/vatType** — Find vat types corresponding with sent data.
- `PUT` **/ledger/vatType/createRelativeVatType** — Create a new relative VAT Type. These are used if the company has 'forholdsmessig fradrag for inngående MVA'.
- `GET` **/ledger/vatType/{id}** — Get vat type by ID.
- `GET, POST` **/ledger/voucher** — Find vouchers corresponding with sent data.
- `GET` **/ledger/voucher/>externalVoucherNumber** — Find vouchers based on the external voucher number.
- `GET` **/ledger/voucher/>nonPosted** — Find non-posted vouchers.
- `GET` **/ledger/voucher/>voucherReception** — Find vouchers in voucher reception.
- `PUT` **/ledger/voucher/historical/:closePostings** — [BETA] Close postings.
- `PUT` **/ledger/voucher/historical/:reverseHistoricalVouchers** — [BETA] Deletes all historical vouchers. Requires the "All vouchers" and "Advanced Voucher" permissions.
- `POST` **/ledger/voucher/historical/employee** — [BETA] Create one employee, based on import from external system. Validation is less strict, ie. employee department isn't required.
- `POST` **/ledger/voucher/historical/historical** — API endpoint for creating historical vouchers. These are vouchers created outside Tripletex, and should be from closed accounting years. The intended usage is to get access to historical transcations in Tripletex. Also creates postings. All amount fields in postings will be used. VAT postings must be included, these are not generated automatically like they are for normal vouchers in Tripletex. Requires the \"All vouchers\" and \"Advanced Voucher\" permissions.
- `POST` **/ledger/voucher/historical/{voucherId}/attachment** — Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). Valid document formats are PDF, PNG, JPEG and TIFF. Non PDF formats will be converted to PDF. Send as multipart form.
- `POST` **/ledger/voucher/importDocument** — Upload a document to create one or more vouchers. Valid document formats are PDF, PNG, JPEG and TIFF. EHF/XML is possible with agreement with Tripletex. Send as multipart form.
- `POST` **/ledger/voucher/importGbat10** — Import GBAT10. Send as multipart form.
- `PUT` **/ledger/voucher/list** — Update multiple vouchers. Postings with guiRow==0 will be deleted and regenerated.
- `GET, POST, DELETE` **/ledger/voucher/openingBalance** — [BETA] Get the voucher for the opening balance.
- `GET` **/ledger/voucher/openingBalance/>correctionVoucher** — [BETA] Get the correction voucher for the opening balance.
- `GET, PUT, DELETE` **/ledger/voucher/{id}** — Get voucher by ID.
- `PUT` **/ledger/voucher/{id}/:reverse** — Reverses the voucher, and returns the reversed voucher. Supports reversing most voucher types, except salary transactions.
- `PUT` **/ledger/voucher/{id}/:sendToInbox** — Send voucher to inbox.
- `PUT` **/ledger/voucher/{id}/:sendToLedger** — Send voucher to ledger.
- `GET` **/ledger/voucher/{id}/options** — Returns a data structure containing meta information about operations that are available for this voucher. Currently only implemented for DELETE: It is possible to check if the voucher is deletable.
- `POST, DELETE` **/ledger/voucher/{voucherId}/attachment** — Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). Valid document formats are PDF, PNG, JPEG and TIFF. Non PDF formats will be converted to PDF. Send as multipart form.
- `GET` **/ledger/voucher/{voucherId}/pdf** — Get PDF representation of voucher by ID.
- `POST` **/ledger/voucher/{voucherId}/pdf/{fileName}** — [DEPRECATED] Use POST ledger/voucher/{voucherId}/attachment instead.
- `GET` **/ledger/voucherType** — Find voucher types corresponding with sent data.
- `GET` **/ledger/voucherType/{id}** — Get voucher type by ID.

## order (21 endpoints)

- `GET, POST` **/order** — Find orders corresponding with sent data.
- `PUT` **/order/:invoiceMultipleOrders** — [BETA] Charges a single customer invoice from multiple orders. The orders must be to the same customer, currency, due date, receiver email, attn. and smsNotificationNumber
- `POST` **/order/list** — [BETA] Create multiple Orders with OrderLines. Max 100 at a time.
- `GET` **/order/orderConfirmation/{orderId}/pdf** — Get PDF representation of order by ID.
- `GET, PUT, POST` **/order/orderGroup** — Find orderGroups corresponding with sent data.
- `GET, DELETE` **/order/orderGroup/{id}** — Get orderGroup by ID. A orderGroup is a way to group orderLines, and add comments and subtotals
- `POST` **/order/orderline** — Create order line. When creating several order lines, use /list for better performance.
- `POST` **/order/orderline/list** — Create multiple order lines.
- `GET` **/order/orderline/orderLineTemplate** — [BETA] Get order line template from order and product
- `GET, PUT, DELETE` **/order/orderline/{id}** — Get order line by ID.
- `PUT` **/order/orderline/{id}/:pickLine** — [BETA] Pick order line. This is only available for customers who have Logistics and who activated the available inventory functionality.
- `PUT` **/order/orderline/{id}/:unpickLine** — [BETA] Unpick order line.This is only available for customers who have Logistics and who activated the available inventory functionality.
- `GET` **/order/packingNote/{orderId}/pdf** — Get PDF representation of packing note by ID.
- `PUT` **/order/sendInvoicePreview/{orderId}** — Send Invoice Preview to customer by email.
- `PUT` **/order/sendOrderConfirmation/{orderId}** — Send Order Confirmation to customer by email.
- `PUT` **/order/sendPackingNote/{orderId}** — Send Packing Note to customer by email.
- `GET, PUT, DELETE` **/order/{id}** — Get order by ID.
- `PUT` **/order/{id}/:approveSubscriptionInvoice** — To create a subscription invoice, first create a order with the subscription enabled, then approve it with this method. This approves the order for subscription invoicing.
- `PUT` **/order/{id}/:attach** — Attach document to specified order ID.
- `PUT` **/order/{id}/:invoice** — Create new invoice or subscription invoice from order.
- `PUT` **/order/{id}/:unApproveSubscriptionInvoice** — Unapproves the order for subscription invoicing.

## product (30 endpoints)

- `GET, POST` **/product** — Find products corresponding with sent data.
- `GET` **/product/discountGroup** — Find discount groups corresponding with sent data.
- `GET` **/product/discountGroup/{id}** — Get discount group by ID.
- `GET` **/product/external** — [BETA] Find external products corresponding with sent data. The sorting-field is not in use on this endpoint.
- `GET` **/product/external/{id}** — [BETA] Get external product by ID.
- `GET, POST` **/product/group** — Find product group with sent data. Only available for Logistics Basic.
- `PUT, POST, DELETE` **/product/group/list** — Update a list of product groups. Only available for Logistics Basic.
- `GET` **/product/group/query** — Wildcard search. Only available for Logistics Basic.
- `GET, PUT, DELETE` **/product/group/{id}** — Find product group by ID. Only available for Logistics Basic.
- `GET, POST` **/product/groupRelation** — Find product group relation with sent data. Only available for Logistics Basic.
- `POST, DELETE` **/product/groupRelation/list** — Add multiple products group relations. Only available for Logistics Basic.
- `GET, DELETE` **/product/groupRelation/{id}** — Find product group relation by ID. Only available for Logistics Basic.
- `GET, POST` **/product/inventoryLocation** — Find inventory locations by product ID. Only available for Logistics Basic.
- `PUT, POST` **/product/inventoryLocation/list** — Update multiple product inventory locations. Only available for Logistics Basic.
- `GET, PUT, DELETE` **/product/inventoryLocation/{id}** — Get inventory location by ID. Only available for Logistics Basic.
- `PUT, POST` **/product/list** — Update a list of products.
- `GET, PUT` **/product/logisticsSettings** — Get logistics settings for the logged in company.
- `GET` **/product/productPrice** — Find prices for a product. Only available for Logistics Basic.
- `GET, POST` **/product/supplierProduct** — Find products corresponding with sent data.
- `POST` **/product/supplierProduct/getSupplierProductsByIds** — Find the products by ids. Method was added as a POST because GET request header has a maximum size that we can exceed with customers that a lot of products.
- `PUT, POST` **/product/supplierProduct/list** — Update a list of supplierProduct.
- `GET, PUT, DELETE` **/product/supplierProduct/{id}** — Get supplierProduct by ID.
- `GET, POST` **/product/unit** — Find product units corresponding with sent data.
- `PUT, POST` **/product/unit/list** — Update list of product units.
- `GET` **/product/unit/master** — Find product units master corresponding with sent data.
- `GET` **/product/unit/master/{id}** — Get product unit master by ID.
- `GET` **/product/unit/query** — Wildcard search.
- `GET, PUT, DELETE` **/product/unit/{id}** — Get product unit by ID.
- `GET, PUT, DELETE` **/product/{id}** — Get product by ID.
- `POST, DELETE` **/product/{id}/image** — Upload image to product. Existing image on product will be replaced if exists

## project (47 endpoints)

- `GET, POST, DELETE` **/project** — Find projects corresponding with sent data.
- `GET` **/project/>forTimeSheet** — Find projects applicable for time sheet registration on a specific day.
- `GET` **/project/batchPeriod/budgetStatusByProjectIds** — Get the budget status for the projects in the specific period.
- `GET` **/project/batchPeriod/invoicingReserveByProjectIds** — Get the invoicing reserve for the projects in the specific period.
- `GET, POST` **/project/category** — Find project categories corresponding with sent data.
- `GET, PUT` **/project/category/{id}** — Find project category by ID.
- `GET` **/project/controlForm** — [BETA] Get project control forms by project ID.
- `GET` **/project/controlForm/{id}** — [BETA] Get project control form by ID.
- `GET` **/project/controlFormType** — [BETA] Get project control form types
- `GET` **/project/controlFormType/{id}** — [BETA] Get project control form type by ID.
- `PUT` **/project/dynamicControlForm/{id}/:copyFieldValuesFromLastEditedForm** — Into each section in the specified form that only has empty or default values, and copyFieldValuesByDefault set as true in the form's template, copy field values from the equivalent section in the most recently edited control form. Signed or completed forms will not be affected.
- `GET, POST` **/project/hourlyRates** — Find project hourly rates corresponding with sent data.
- `DELETE` **/project/hourlyRates/deleteByProjectIds** — Delete project hourly rates by project id.
- `PUT, POST, DELETE` **/project/hourlyRates/list** — Update multiple project hourly rates.
- `GET, POST` **/project/hourlyRates/projectSpecificRates** — Find project specific rates corresponding with sent data.
- `PUT, POST, DELETE` **/project/hourlyRates/projectSpecificRates/list** — Update multiple project specific rates.
- `GET, PUT, DELETE` **/project/hourlyRates/projectSpecificRates/{id}** — Find project specific rate by ID.
- `PUT` **/project/hourlyRates/updateOrAddHourRates** — Update or add the same project hourly rate from project overview.
- `GET, PUT, DELETE` **/project/hourlyRates/{id}** — Find project hourly rate by ID.
- `POST` **/project/import** — Upload project import file.
- `PUT, POST, DELETE` **/project/list** — [BETA] Update multiple projects.
- `GET` **/project/number/{number}** — Find project by number.
- `GET, POST` **/project/orderline** — [BETA] Find all order lines for project.
- `POST` **/project/orderline/list** — [BETA] Create multiple order lines.
- `GET` **/project/orderline/orderLineTemplate** — [BETA] Get order line template from project and product
- `GET` **/project/orderline/query** — [BETA] Wildcard search.
- `GET, PUT, DELETE` **/project/orderline/{id}** — [BETA] Get order line by ID.
- `POST` **/project/participant** — [BETA] Add new project participant.
- `POST, DELETE` **/project/participant/list** — [BETA] Add new project participant. Multiple project participants can be sent in the same request.
- `GET, PUT` **/project/participant/{id}** — [BETA] Find project participant by ID.
- `POST` **/project/projectActivity** — Add project activity.
- `DELETE` **/project/projectActivity/list** — Delete project activities
- `GET, DELETE` **/project/projectActivity/{id}** — Find project activity by id
- `GET` **/project/resourcePlanBudget** — Get resource plan entries in the specified period.
- `GET, PUT` **/project/settings** — Get project settings of logged in company.
- `GET, POST` **/project/subcontract** — Find project sub-contracts corresponding with sent data.
- `GET` **/project/subcontract/query** — Wildcard search.
- `GET, PUT, DELETE` **/project/subcontract/{id}** — Find project sub-contract by ID.
- `GET` **/project/task** — Find all tasks for project.
- `GET` **/project/template/{id}** — Get project template by ID.
- `GET, PUT, DELETE` **/project/{id}** — Find project by ID.
- `GET` **/project/{id}/period/budgetStatus** — Get the budget status for the project period
- `GET` **/project/{id}/period/hourlistReport** — Find hourlist report by project period.
- `GET` **/project/{id}/period/invoiced** — Find invoiced info by project period.
- `GET` **/project/{id}/period/invoicingReserve** — Find invoicing reserve by project period.
- `GET` **/project/{id}/period/monthlyStatus** — Find overall status by project period.
- `GET` **/project/{id}/period/overallStatus** — Find overall status by project period.

## salary (38 endpoints)

- `GET` **/salary/compilation** — Find salary compilation by employee.
- `GET` **/salary/compilation/pdf** — Find salary compilation (PDF document) by employee.
- `POST` **/salary/financeTax/reconciliation/context** — Create a financeTax reconciliation context for a customer
- `GET` **/salary/financeTax/reconciliation/{reconciliationId}/overview** — Get finance tax overview for a specific reconciliation term
- `GET` **/salary/financeTax/reconciliation/{reconciliationId}/paymentsOverview** — Get finance tax payment overview from start of year to the current reconciliation term
- `POST` **/salary/holidayAllowance/reconciliation/context** — Create a holiday allowance reconciliation context for a customer
- `GET` **/salary/holidayAllowance/reconciliation/{reconciliationId}/holidayAllowanceDetails** — Get a holiday allowance details for the current reconciliation term
- `GET` **/salary/holidayAllowance/reconciliation/{reconciliationId}/holidayAllowanceSummary** — Salary holiday allowance reconciliation summary
- `POST` **/salary/mandatoryDeduction/reconciliation/context** — Create a mandatoryDeduction reconciliation context for a customer
- `GET` **/salary/mandatoryDeduction/reconciliation/{reconciliationId}/overview** — Salary mandatory deduction reconciliation overview
- `GET` **/salary/mandatoryDeduction/reconciliation/{reconciliationId}/paymentsOverview** — Get mandatory deduction payments overview from start of year to the current reconciliation term
- `POST` **/salary/payrollTax/reconciliation/context** — Create a payroll tax reconciliation context for a customer
- `GET` **/salary/payrollTax/reconciliation/{reconciliationId}/overview** — Salary payroll tax reconciliation overview
- `GET` **/salary/payrollTax/reconciliation/{reconciliationId}/paymentsOverview** — Get a payroll tax payments from start of year to the current reconciliation term
- `GET` **/salary/payslip** — Find payslips corresponding with sent data.
- `GET` **/salary/payslip/{id}** — Find payslip by ID.
- `GET` **/salary/payslip/{id}/pdf** — Find payslip (PDF document) by ID.
- `GET, PUT` **/salary/settings** — Get salary settings of logged in company.
- `GET, POST` **/salary/settings/holiday** — Find holiday settings of current logged in company.
- `PUT, POST, DELETE` **/salary/settings/holiday/list** — Update multiple holiday settings of current logged in company.
- `PUT` **/salary/settings/holiday/{id}** — Update a holiday setting of current logged in company.
- `GET, POST` **/salary/settings/pensionScheme** — Find pension schemes.
- `PUT, POST, DELETE` **/salary/settings/pensionScheme/list** — Update multiple Pension Schemes.
- `GET, PUT, DELETE` **/salary/settings/pensionScheme/{id}** — Get Pension Scheme for a specific ID
- `GET, POST` **/salary/settings/standardTime** — Get all standard times.
- `GET` **/salary/settings/standardTime/byDate** — Find standard time by date
- `GET, PUT` **/salary/settings/standardTime/{id}** — Find standard time by ID.
- `POST` **/salary/taxDeduction/reconciliation/context** — Create a taxDeduction reconciliation context for a customer
- `GET` **/salary/taxDeduction/reconciliation/{reconciliationId}/balanceAndOwedAmount** — Get tax deduction details for a reconciliation
- `GET` **/salary/taxDeduction/reconciliation/{reconciliationId}/overview** — Get salary tax deduction data for the reconciliation table
- `GET` **/salary/taxDeduction/reconciliation/{reconciliationId}/paymentsOverview** — Get salary tax deduction payment overview from start of year to the current reconciliation term
- `POST` **/salary/transaction** — Create a new salary transaction.
- `GET, DELETE` **/salary/transaction/{id}** — Find salary transaction by ID.
- `POST` **/salary/transaction/{id}/attachment** — Upload an attachment to a salary transaction
- `POST` **/salary/transaction/{id}/attachment/list** — Upload multiple attachments to a salary transaction
- `PUT` **/salary/transaction/{id}/deleteAttachment** — Delete attachment.
- `GET` **/salary/type** — Find salary type corresponding with sent data.
- `GET` **/salary/type/{id}** — Find salary type by ID.

## travelExpense (43 endpoints)

- `GET, POST` **/travelExpense** — Find travel expenses corresponding with sent data.
- `PUT` **/travelExpense/:approve** — Approve travel expenses.
- `PUT` **/travelExpense/:copy** — Copy travel expense.
- `PUT` **/travelExpense/:createVouchers** — Create vouchers
- `PUT` **/travelExpense/:deliver** — Deliver travel expenses.
- `PUT` **/travelExpense/:unapprove** — Unapprove travel expenses.
- `PUT` **/travelExpense/:undeliver** — Undeliver travel expenses.
- `GET, POST` **/travelExpense/accommodationAllowance** — Find accommodation allowances corresponding with sent data.
- `GET, PUT, DELETE` **/travelExpense/accommodationAllowance/{id}** — Get travel accommodation allowance by ID.
- `GET, POST` **/travelExpense/cost** — Find costs corresponding with sent data.
- `PUT` **/travelExpense/cost/list** — Update costs.
- `GET, PUT, DELETE` **/travelExpense/cost/{id}** — Get cost by ID.
- `GET` **/travelExpense/costCategory** — Find cost category corresponding with sent data.
- `GET` **/travelExpense/costCategory/{id}** — Get cost category by ID.
- `POST` **/travelExpense/costParticipant** — Create participant on cost.
- `POST` **/travelExpense/costParticipant/createCostParticipantAdvanced** — Create participant on cost using explicit parameters
- `POST, DELETE` **/travelExpense/costParticipant/list** — Create participants on cost.
- `GET` **/travelExpense/costParticipant/{costId}/costParticipants** — Get cost's participants by costId.
- `GET, DELETE` **/travelExpense/costParticipant/{id}** — Get cost participant by ID.
- `POST` **/travelExpense/drivingStop** — Create mileage allowance driving stop.
- `GET, DELETE` **/travelExpense/drivingStop/{id}** — Get driving stop by ID.
- `GET, POST` **/travelExpense/mileageAllowance** — Find mileage allowances corresponding with sent data.
- `GET, PUT, DELETE` **/travelExpense/mileageAllowance/{id}** — Get mileage allowance by ID.
- `GET, POST` **/travelExpense/passenger** — Find passengers corresponding with sent data.
- `POST, DELETE` **/travelExpense/passenger/list** — Create passengers.
- `GET, PUT, DELETE` **/travelExpense/passenger/{id}** — Get passenger by ID.
- `GET` **/travelExpense/paymentType** — Find payment type corresponding with sent data.
- `GET` **/travelExpense/paymentType/{id}** — Get payment type by ID.
- `GET, POST` **/travelExpense/perDiemCompensation** — Find per diem compensations corresponding with sent data.
- `GET, PUT, DELETE` **/travelExpense/perDiemCompensation/{id}** — Get per diem compensation by ID.
- `GET` **/travelExpense/rate** — Find rates corresponding with sent data.
- `GET` **/travelExpense/rate/{id}** — Get travel expense rate by ID.
- `GET` **/travelExpense/rateCategory** — Find rate categories corresponding with sent data.
- `GET` **/travelExpense/rateCategory/{id}** — Get travel expense rate category by ID.
- `GET` **/travelExpense/rateCategoryGroup** — Find rate categoriy groups corresponding with sent data.
- `GET` **/travelExpense/rateCategoryGroup/{id}** — Get travel report rate category group by ID.
- `GET` **/travelExpense/settings** — Get travel expense settings of logged in company.
- `GET` **/travelExpense/zone** — Find travel expense zones corresponding with sent data.
- `GET` **/travelExpense/zone/{id}** — Get travel expense zone by ID.
- `GET, PUT, DELETE` **/travelExpense/{id}** — Get travel expense by ID.
- `PUT` **/travelExpense/{id}/convert** — Convert travel to/from employee expense.
- `GET, POST, DELETE` **/travelExpense/{travelExpenseId}/attachment** — Get attachment by travel expense ID.
- `POST` **/travelExpense/{travelExpenseId}/attachment/list** — Upload multiple attachments to travel expense.
