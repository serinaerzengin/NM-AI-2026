## TRIPLETEX DATA MODEL — key relationships

### Invoice & Orders
- To create an invoice: first POST /order (with orderLines), then PUT /order/{id}/:invoice
- PUT /order/{id}/:invoice is a query-param-only endpoint: use params (invoiceDate required), NO request body
- To register payment: GET /invoice/paymentType first, then PUT /invoice/{id}/:payment with params paymentDate, paymentTypeId, paidAmount
- To credit/reverse: PUT /invoice/{id}/:createCreditNote with params (date is auto-set)
- Order needs: customer (object with id), orderDate, orderLines array
- OrderLine needs: product (object with id) or description, count, unitPriceExcludingVatCurrency
- When products referenced by number, first GET /product?number=XXXX to get ID
- VAT on order lines: vatType (object with id). 25% standard = id 3, 15% food = id 32, 0% exempt = id 6

### Supplier Invoice (incoming)
- NO "POST /supplierInvoice" endpoint. Register via POST /ledger/voucher:
  1. GET /supplier or POST /supplier to get supplier
  2. POST /ledger/voucher: debit expense account, credit 2400 (AP)
  3. GET /ledger/account?numberFrom=X&numberTo=X to find account IDs

### Voucher (Manual Journal Entry)
- POST /ledger/voucher: date, description, postings array
- Each posting: account (object with id), amount (positive=debit, negative=credit)
- Optional: description, customer, supplier, department, project, freeAccountingDimension1/2/3
- Postings must balance (sum = 0)
- Common accounts: 1920=Bank, 2400=Leverandørgjeld, 2700=Lønnsgjeld, 4000=Varekostnad, 5000=Lønn, 6300=Leie, 6340=Lys/varme, 6500=Kontorkostnader, 6860=Kontorrekvisita, 7000=Reisekostnader, 7100=Bilkostnader, 7140=Reise og diett, 7300=Markedsføring

### Employee
- Needs: firstName, lastName, dateOfBirth, email, userType ("STANDARD"), department (object with id — GET /department first)
- Start date in employments array: [{"startDate": "YYYY-MM-DD", "isMainEmployer": true}]

### Salary / Payroll
- POST /salary/transaction: date, year, month, payslips array
- IMPORTANT: date, year, month must be set at BOTH the transaction level AND inside each payslip
- Each payslip: employee (object with id), date, year, month, specifications array
- Each specification: salaryType (object with id), count, rate
- GET /salary/type first for valid types (search by name e.g. "Fastlønn", "Bonus", "Feriepenger")
- Employee MUST have active employment in the period

### Project
- POST /project: name, projectManager (object with id — an employee), startDate, endDate
- For fixed-price: set fixedPrice, then create order with partial amount and invoice it

### Timesheet
- POST /timesheet/entry: employee, project, activity (all objects with id), date, hours
- Date must be >= project startDate. GET /activity to find or POST /activity to create.

### Accounting Dimensions
- POST /ledger/accountingDimensionName: use field "dimensionName" for the name
- POST /ledger/accountingDimensionValue: use "displayName" for name, "dimensionIndex" (int 1-3) for which dimension
- Link to voucher posting via freeAccountingDimension1/2/3 (object with id)

### Travel Expense
- POST /travelExpense: employee (object with id), title, costs array (inline)
- Each cost: costCategory (object with id), paymentType (object with id), amountCurrencyIncVat, date
- To find valid categories: GET /travelExpense/costCategory
- To find valid payment types: GET /travelExpense/paymentType
- Alternatively, costs can be added separately via POST /travelExpense/cost with travelExpense ref

### General
- Dates: "YYYY-MM-DD" format
- References: use object with id, e.g. {"id": 42}
- Lookup by org number: GET /customer?organizationNumber=xxx or GET /supplier?organizationNumber=xxx
- Existing entities: use GET to find them. Only POST to create NEW ones.
- Action endpoints (/:invoice, /:payment, /:createCreditNote) use query params, NOT request body
