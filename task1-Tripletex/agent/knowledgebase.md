# Tripletex Domain Knowledge

Accounting workflow rules that the API schema alone does not tell you.
The decomposer and executor read this to avoid common mistakes.

---

## Employee Creation

**Endpoint:** `POST /employee`

**Required fields the schema doesn't mark:**
- `department` — ALWAYS required. Do `GET /department` first to get an ID.
- `userType` — ALWAYS required. Use enum: `STANDARD`, `EXTENDED`, or `NO_ACCESS`.

**Workflow:**
1. `GET /department` → get first department ID
2. `POST /employee` with `firstName`, `lastName`, `email`, `userType: "STANDARD"`, `department: {"id": <dept_id>}`, `dateOfBirth` (if given, format `"YYYY-MM-DD"`)
3. ALWAYS grant admin: `PUT /employee/entitlement/:grantEntitlementsByTemplate` with query params `employeeId=<id>` and `template=ALL_PRIVILEGES`
4. IF `startDate` given → `POST /employee/employment` with:
   - `employee: {"id": <emp_id>}`
   - `startDate: "YYYY-MM-DD"`
   - `employmentDetails: [{"date": "<startDate>", "employmentType": "ORDINARY"}]`

**Date formats:** ALWAYS use `YYYY-MM-DD` (e.g. "1991-06-04" for June 4, 1991).

**DO NOT** call `GET /country` or `GET /employee/category` — these are unnecessary and waste API calls.

---

## Customer Creation

**Endpoint:** `POST /customer`

**Minimal required fields:** `name`, `isCustomer: true`

**Optional but commonly needed:** `email`, `organizationNumber`, `phoneNumber`

**Address fields:** Include address inline (NOT as a _ref):
```json
{
  "name": "Oceano Lda",
  "isCustomer": true,
  "organizationNumber": "945727098",
  "email": "post@oceano.no",
  "postalAddress": {
    "addressLine1": "Industriveien 56",
    "postalCode": "4611",
    "city": "Kristiansand"
  },
  "physicalAddress": {
    "addressLine1": "Industriveien 56",
    "postalCode": "4611",
    "city": "Kristiansand"
  }
}
```
**IMPORTANT:** Set BOTH `postalAddress` and `physicalAddress` to the same address if only one address is given.

**Workflow:** Usually a single `POST /customer` is enough. No prerequisite GETs needed.

---

## Supplier Registration

**Endpoint:** `POST /supplier`

**Required fields:** `name`, `isSupplier: true`

**All commonly scored fields:**
- `name` — REQUIRED
- `isSupplier: true` — REQUIRED (same pattern as customer's isCustomer)
- `organizationNumber` — send if given
- `email` — send if given
- `phoneNumber` — send if given

**Workflow:** Single `POST /supplier` with ALL provided fields.

---

## Product Creation

**Endpoint:** `POST /product`

**Minimal required fields:** `name`

**All commonly needed fields:**
- `name` — the product name (REQUIRED)
- `number` — the product number/code (string, e.g. "8115"). ALWAYS set this if given in the task.
- `priceExcludingVatCurrency` — selling price excl. VAT (number). This is the SELLING price.
- `priceIncludingVatCurrency` — selling price incl. VAT (number). Set this too if you have the excl. price + VAT rate.
- `vatType: {"id": <id>}` — VAT type. Use the hardcoded IDs below.

**VAT type selection for PRODUCTS (outgoing/selling) — hardcoded IDs, do NOT call GET /ledger/vatType:**
- 25% standard → `vatType: {"id": 3}`
- 15% food (næringsmiddel) → `vatType: {"id": 31}`
- 12% transport → `vatType: {"id": 32}`
- 0% exempt (avgiftsfri) → `vatType: {"id": 5}`

**IMPORTANT:** Do NOT use id=1 for products — that's INPUT/incoming VAT. Products use OUTGOING VAT (utgående).

**Workflow:**
1. `POST /product` with `name`, `number`, `priceExcludingVatCurrency`, `vatType: {"id": <id>}`
   Use the hardcoded VAT IDs above — do NOT waste an API call on `GET /ledger/vatType`.
   If a hardcoded ID fails with 422, fall back to `GET /ledger/vatType` to find the correct ID.

---

## Department Creation

**Endpoint:** `POST /department`

**Required fields:** `name`, `departmentNumber`

**The `departmentManager` _ref is optional** — Tripletex accepts departments without a manager.

**Multiple departments:** Create each one with a separate `POST /department` call.

---

## Invoice Creation (Outgoing)

**Endpoint:** `POST /invoice`

**CRITICAL PREREQUISITE:** Invoices require the company to have a bank account number registered.
If `POST /invoice` returns "Faktura kan ikke opprettes før selskapet har registrert et bankkontonummer":
- This is a Tripletex company configuration issue, NOT something the agent can fix via API.
- Do NOT try to register a bank account via API — `PUT /company` is blocked by the proxy.
- Do NOT waste turns trying workarounds. Just proceed with creating the order (it will still be scored for the order/product/customer creation).

**This is a multi-step workflow:**
1. Customer must exist → `GET /customer` by name or org number. If not found, `POST /customer` with `name`, `isCustomer: true`, and `organizationNumber` if given.
2. Product(s) must exist → For each product: `GET /product` by name. If not found, `POST /product` with `name`, `number` (product number), `priceExcludingVatCurrency`, `vatType: {"id": <vat_id>}`.
3. Create order → `POST /order` with `customer: {"id": <id>}`, `orderDate` (today), `deliveryDate` (today), and `orderLines` array.
4. Create invoice → `POST /invoice` with `invoiceDate`, `invoiceDueDate`, `customer: {"id": <id>}`, `orders: [{"id": <order_id>}]`

**Order lines** (inside `POST /order` → `orderLines` array):
Each line needs: `product: {"id": <id>}`, `count: 1`, `unitPriceExcludingVatCurrency: <amount>`, `vatType: {"id": <vat_id>}`

**Multiple products with different VAT rates:** Create each product with its own `vatType`, then add each as a separate order line.

**"Send" the invoice:** After creating, some tasks ask to "send" it. Use `PUT /invoice/{id}/:send` with `sendType` query param (e.g. "EMAIL").

---

## Payment Registration & Reversal

**Register payment on invoice:**
`PUT /invoice/{invoiceId}/:payment` with query params:
- `paymentDate`: "YYYY-MM-DD" (today)
- `paymentTypeId`: `<id>` (from `GET /invoice/paymentType`)
- `paidAmount`: `<amount>` (positive number, the full invoice amount incl. VAT)

**Reverse a payment (bank return):**
Same endpoint, but with NEGATIVE paidAmount:
- `paidAmount`: `-<amount_incl_vat>`
- The amount must be a plain number — no text, no currency suffix

**Workflow for reversal:**
1. `GET /customer` — find by org number
2. `GET /invoice` — find the invoice (filter by customerId + date range)
3. `GET /invoice/paymentType` — get payment type ID
4. `PUT /invoice/{id}/:payment` with `paymentDate=today`, `paymentTypeId=<id>`, `paidAmount=-<amount_incl_vat>`

**Calculate amount incl. VAT:** If task gives "X NOK excl. VAT" with 25% rate: `amount_incl = X × 1.25`

For supplier invoices: `POST /supplierInvoice/{invoiceId}/:addPayment`

---

## Supplier Invoice (Incoming Invoice)

**This is NOT a direct POST to /supplierInvoice.** Supplier invoices are created through the voucher system.

**Workflow:**
1. Ensure supplier exists → `GET /supplier` by name/org number. If not found, `POST /supplier` with `name`, `isSupplier: true`
2. Get expense account ID → `GET /ledger/account?number=<account_number>` (e.g. 6500 for office services)
3. Get supplier liability account → `GET /ledger/account?number=2400`
4. Get VAT receivable account → `GET /ledger/account?number=2710` (for deductible input VAT)
5. Get voucher type → `GET /ledger/voucherType` — find the supplier invoice type (look for name containing "Leverandør" or use the first available)
6. Create voucher → `POST /ledger/voucher` with:
   - `date`: invoice date (today if not specified)
   - `description`: e.g. "Supplier invoice INV-XXXX from SupplierName"
   - `voucherType: {"id": <voucher_type_id>}`
   - `postings`: array with THREE postings that must balance to zero:

**Example — supplier invoice 56300 NOK incl. 25% VAT:**
- Net amount = 56300 / 1.25 = 45040
- VAT amount = 56300 - 45040 = 11260

```json
{
  "date": "2026-03-20",
  "description": "Supplier invoice INV-2026-4914 from Océan SARL",
  "voucherType": {"id": "<supplier_voucher_type_id>"},
  "postings": [
    {
      "account": {"id": "<expense_acct_6500>"},
      "amount": 45040,
      "supplier": {"id": "<supplier_id>"},
      "invoiceNumber": "INV-2026-4914",
      "vatType": {"id": "<vat_25pct_input_id>"}
    },
    {
      "account": {"id": "<vat_acct_2710>"},
      "amount": 11260
    },
    {
      "account": {"id": "<liability_acct_2400>"},
      "amount": -56300,
      "supplier": {"id": "<supplier_id>"},
      "invoiceNumber": "INV-2026-4914"
    }
  ]
}
```

**IMPORTANT:**
- All three postings must sum to zero (45040 + 11260 + (-56300) = 0).
- `vatType` goes ONLY on the expense posting (account 6500), NOT on account 2710. Account 2710 is locked to VAT code 0 — Tripletex auto-calculates the VAT posting from the expense line's vatType.
- Do NOT get a separate VAT type via `GET /ledger/vatType` — use hardcoded input VAT IDs (see Common Patterns below).

---

## Salary / Payroll

**Endpoint:** `POST /salary/transaction`

**Workflow:**
1. `GET /employee` — find employee by email/name to get ID
2. `GET /employee/employment?employeeId=<id>` — verify active employment exists for the period
3. `GET /salary/type` — find salary type IDs:
   - "Fastlønn" or "Fast lønn" = base/fixed salary
   - "Bonus" or "Engangsutbetaling" = one-time bonus
4. `POST /salary/transaction` with:

```json
{
  "date": "2026-03-31",
  "year": 2026,
  "month": 3,
  "payslips": [
    {
      "employee": {"id": "<employee_id>"},
      "date": "2026-03-31",
      "year": 2026,
      "month": 3,
      "specifications": [
        {"salaryType": {"id": "<base_salary_type_id>"}, "rate": 56900, "count": 1},
        {"salaryType": {"id": "<bonus_type_id>"}, "amount": 15800, "count": 1}
      ]
    }
  ]
}
```

**Key gotchas:**
- Employee must have an active employment in the period. Check with `GET /employee/employment`.
- Use `rate` for recurring amounts (base salary), `amount` for fixed one-time amounts (bonus).
- The `date` should be the last day of the salary month.
- Use `generateTaxDeduction=true` query parameter to auto-calculate tax.

---

## Travel Expense

**Workflow:**
1. `GET /employee` — find employee by email
2. `POST /travelExpense` — create the travel report:
```json
{
  "employee": {"id": "<emp_id>"},
  "title": "Trip description",
  "travelDetails": {
    "isForeignTravel": false,
    "isDayTrip": false,
    "departureDate": "2026-03-17",
    "returnDate": "2026-03-20",
    "departureFrom": "Oslo",
    "destination": "Bergen",
    "departureTime": "08:00",
    "returnTime": "17:00",
    "purpose": "work"
  },
  "isChargeable": false,
  "isFixedInvoicedAmount": false,
  "isIncludeAttachedReceiptsWhenReinvoicing": false
}
```
**CRITICAL:** `travelDetails` is an INLINE object, NOT a `{"id": ...}` reference.
Without `travelDetails`, Tripletex creates an "ansattutlegg" (employee expense) instead of a "reiseregning" (travel report).

3. `GET /travelExpense/rateCategory?type=PER_DIEM_DOMESTIC&isValidDomestic=true&count=10`
4. `GET /travelExpense/rate?rateCategoryId=<cat_id>&count=10`
   MUST filter — unfiltered returns 10K+ results and 422s.

5. `POST /travelExpense/perDiemCompensation`:
```json
{
  "travelExpense": {"id": "<expense_id>"},
  "rateType": {"id": "<rate_id>"},
  "rateCategory": {"id": "<cat_id>"},
  "overnightAccommodation": "HOTEL",
  "location": "Bergen",
  "count": 4,
  "rate": 800,
  "amount": 3200
}
```
Do NOT include `countryCode` — the sandbox may not have countries enabled.

6. `GET /travelExpense/paymentType` — get valid payment type ID (use the FIRST result)
7. `GET /currency?code=NOK` — get NOK currency ID

8. `POST /travelExpense/cost` (one per cost item):
```json
{
  "travelExpense": {"id": "<expense_id>"},
  "paymentType": {"id": "<payment_type_id>"},
  "currency": {"id": "<nok_id>"},
  "amountCurrencyIncVat": 7800,
  "date": "2026-03-17",
  "category": "Flight ticket"
}
```

**Do NOT set `isCompleted`** — validation is only enforced on completion. Leave it incomplete.

---

## Accounting Dimensions (Free Dimensions)

**Workflow:**
1. `POST /ledger/accountingDimensionName` — create the dimension with `{"name": "DimensionName"}`
2. `POST /ledger/accountingDimensionValue` — create each value:
   - `displayName`: "ValueName" (the value label)
   - `number`: "1" (a unique number string)
   - `dimensionIndex`: 1 (integer — which dimension slot: 1, 2, or 3)
   - For the first custom dimension, use `dimensionIndex: 1`
   - **DO NOT send `accountingDimensionName` — this field does not exist in the API**
3. Repeat step 2 for additional values (number="2", etc.)
4. `GET /ledger/voucherType` — get voucher type ID
5. `GET /ledger/account?number=<acct_num>` — get account IDs for both debit and credit
6. `POST /ledger/voucher` with postings that reference the dimension values:

```json
{
  "date": "2026-03-20",
  "description": "Dimension posting",
  "voucherType": {"id": "<vt_id>"},
  "postings": [
    {
      "account": {"id": "<expense_acct_id>"},
      "amount": 25000,
      "freeAccountingDimension1": {"id": "<dimension_value_id>"}
    },
    {
      "account": {"id": "<bank_acct_1920_id>"},
      "amount": -25000
    }
  ]
}
```

**IMPORTANT:** The credit side should use account 1920 (bank) or another suitable balance account. NEVER include `row` in postings.

---

## Voucher Posting (General)

**Endpoint:** `POST /ledger/voucher`

**Key rules:**
- Postings MUST balance to zero (sum of all amounts = 0)
- Debit amounts are positive, credit amounts are negative
- Each posting needs at minimum: `account: {"id": <id>}`, `amount`
- Get account by number: `GET /ledger/account?number=<num>`
- Get voucher type: `GET /ledger/voucherType`

**Example:**
```json
{
  "date": "2026-03-20",
  "description": "Description here",
  "voucherType": {"id": "<voucher_type_id>"},
  "postings": [
    {"account": {"id": "<debit_account_id>"}, "amount": 25000},
    {"account": {"id": "<credit_account_id>"}, "amount": -25000}
  ]
}
```

**CRITICAL RULES:**
- **NEVER include `row` field in postings.** Tripletex auto-assigns row numbers. Including `row: 0` causes "systemgenererte" errors.
- **Only include fields with actual values. NEVER send null fields in postings** — strip them. Sending `account.name: null` causes validation errors.

---

## Project Creation

**Endpoint:** `POST /project`

**Required:** `name`, `number`, `projectManager: {"id": <employee_id>}`, `startDate`

**Optionally linked to:** `customer`, `department`

---

## Project — Hourly Billing

Register hours for an employee on a project activity, then generate a project invoice.

**Workflow:**
1. `GET /customer` — find customer by name/org number
2. `POST /customer` — create if not found (with `isCustomer: true`)
3. `GET /employee` — find employee by email
4. `POST /employee` — create if not found (with department, userType)
5. `POST /project` — create project with:
   - `name`, `number`: "1" (or any unique string)
   - `projectManager: {"id": <employee_id>}`
   - `customer: {"id": <customer_id>}`
   - `startDate`: today
   - `isInternal: false`
6. `GET /activity` — find or know the activity name
7. `POST /activity` — create activity if not found: `{"name": "ActivityName"}`
8. `POST /project/projectActivity` — link activity to project:
   - `project: {"id": <project_id>}`
   - `activity: {"id": <activity_id>}`
   - `budgetHourlyRateCurrency: <hourly_rate>`
9. `POST /timesheet/entry` — register hours:
   - `project: {"id": <project_id>}`
   - `activity: {"id": <activity_id>}`
   - `employee: {"id": <employee_id>}`
   - `date`: today
   - `hours: <number_of_hours>`
10. `POST /order` — create order from project:
    - `customer: {"id": <customer_id>}`
    - `orderDate`: today, `deliveryDate`: today
    - `orderLines: [{"product": {"id": ...}, "count": <hours>, "unitPriceExcludingVatCurrency": <rate>}]`
    NOTE: May need to create a product for the billing line item. Use `POST /order` with inline `orderLines`, NOT the BETA `POST /project/orderline` (returns 403).
11. `POST /invoice` — create invoice from order

---

## Project — Fixed Price Billing

Set a fixed price on a project and invoice a percentage as a milestone payment.

**Workflow:**
1. `GET /customer` → find/create customer
2. `GET /employee` → find/create employee
3. `POST /project` with:
   - `name`, `number`: "1", `startDate`: today
   - `projectManager: {"id": <emp_id>}`
   - `customer: {"id": <cust_id>}`
   - `isFixedPrice: true`
   - `fixedprice: <total_amount>`
4. Calculate milestone amount: `fixedprice × percentage`
5. `POST /order` with:
   - `customer: {"id": <cust_id>}`
   - `orderDate`: today, `deliveryDate`: today
   - `orderLines: [{"description": "Milestone payment X%", "count": 1, "unitPriceExcludingVatCurrency": <milestone_amount>}]`
   NOTE: For order lines without a product, check if a description-only line works. If not, create a generic product first. Use `POST /order` with inline `orderLines`, NOT the BETA `POST /project/orderline` (returns 403).
6. `POST /invoice` from order

---

## Common Patterns

**"If not found, create":**
Always do a GET first to check existence. If `.values` is empty, create. If found, use the existing ID.
If entity already exists (422 "allerede registrert"), GET it and use the existing ID.

**VAT Types (Norwegian standard rates) — OUTGOING (products/sales, utgående):**
- 25% → vatType id=3 (Utgående avgift, høy sats)
- 15% → vatType id=31 (Utgående avgift, middels sats) — for food/næringsmiddel
- 12% → vatType id=32 (Utgående avgift, lav sats) — transport, hotels
- 0% → vatType id=5 (Ingen utgående avgift, innenfor mva-loven) — exempt/avgiftsfri

**VAT Types — INCOMING (supplier invoices/purchases, inngående):**
- 25% → vatType id=1 (Fradrag inngående avgift, høy sats)
- 15% → vatType id=11 (Fradrag inngående avgift, middels sats)
- 12% → vatType id=12 (Fradrag inngående avgift, lav sats)

**Account numbers (Norwegian standard chart of accounts):**
- 1000-1999: Assets (1920 = bank)
- 2000-2999: Liabilities
  - 2400: Supplier liability (leverandørgjeld)
  - 2710: Deductible input VAT (fradragsberettiget inngående MVA) — **locked to VAT code 0, do NOT set vatType on this account**
- 3000-3999: Revenue
- 4000-4999: Cost of goods sold
- 5000-5999: Salary and personnel costs
- 6000-6999: Other operating costs (6500 = office services)
- 7000-7999: Other operating costs (depreciation, etc.)
- 8000-8999: Financial income/expenses
