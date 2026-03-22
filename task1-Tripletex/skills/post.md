# POST Patterns

## Entities
- Customer: {name, isCustomer:true, email, organizationNumber, postalAddress:{addressLine1,postalCode,city}, physicalAddress:{same}}
- Supplier: {name, isSupplier:true, organizationNumber, postalAddress:{...}, physicalAddress:{...}}
- Employee: {firstName, lastName, email, dateOfBirth, userType:"EXTENDED", department:{id}}. Response includes companyId.
- Product: {name, number(STRING!), priceExcludingVatCurrency, vatType:{id}}
- Department: {name, departmentNumber(unique)}
- Division: {name, startDate, organizationNumber(random 9-digit, NOT company's own), municipalityDate, municipality:{id:301}}

## Admin Role — ALWAYS DO THIS after creating an employee
POST /employee/entitlement {employee:{id:EMP_ID}, customer:{id:COMPANY_ID}, entitlementId:1}
- entitlementId 1 = ROLE_ADMINISTRATOR
- COMPANY_ID comes from the POST /employee response's "companyId" field (inside the value object)
- This is REQUIRED for every employee creation task

## Employment
POST /employee/employment {employee:{id}, division:{id}, startDate, isMainEmployer:true}
- Employee MUST have dateOfBirth set before creating employment
- Division is REQUIRED — GET /division first, create one if none exists

## Employment Details (valid fields ONLY)
POST /employee/employment/details {employment:{id}, date, annualSalary, percentageOfFullTimeEquivalent, employmentType, employmentForm, remunerationType, workingHoursScheme, shiftDurationHours, occupationCode:{id}}
- Do NOT use: workingHoursPerWeek, standardWorkingHours — these don't exist
- ONLY include fields that are EXPLICITLY in the prompt or PDF. Do NOT guess values.
- shiftDurationHours: ONLY if hours per day is stated in the prompt/PDF
- annualSalary: ONLY if salary amount is in the prompt/PDF
- percentageOfFullTimeEquivalent: ONLY if percentage is in the prompt/PDF
- occupationCode: ONLY if a job title is in the prompt/PDF

## Occupation Code Lookup — ONLY when job title is in prompt/PDF
GET /employee/employment/occupationCode?nameNO=KEYWORD — search by Norwegian keyword from job title
- ONLY look up when the prompt or PDF explicitly mentions a job title/position
- Returns Tripletex internal IDs — use directly as occupationCode:{id:INTERNAL_ID}
- Max 3 search attempts with different keywords. If not found, omit occupationCode.

## Orders
POST /order {customer:{id}, orderDate, deliveryDate(REQUIRED), orderLines:[{product:{id}, count}]}
- For PROJECT invoices: MUST include project:{id} in the order body — without it the invoice won't be linked to the project
- NO vatType on orderLines — inherited from product
- deliveryDate defaults to orderDate if not specified

## Vouchers
POST /ledger/voucher {date, description(REQUIRED), voucherType:{id}, postings:[{account:{id}, amountGross, amountGrossCurrency, row(starts at 1)}]}
- Postings MUST sum to 0 (positive=debit, negative=credit)
- Use amountGross+amountGrossCurrency, NOT amount
- NO dueDate field exists on vouchers

## Salary
POST /salary/transaction {date, year, month, payslips:[{employee:{id}, date, year, month, specifications:[{salaryType:{id}, rate(NOT amount), count}]}]}
- Use "rate" not "amount" — amount is auto-calculated
- date/year/month on BOTH transaction AND each payslip
- If "arbeidsforhold" error → create employment first (handled automatically)

## Travel Expense — EXACT workflow (follow this order):
1. POST /travelExpense {title, employee:{id}} → get expense ID
2. PUT /travelExpense/{id}/convert → convert to travel report (REQUIRED)
3. PUT /travelExpense/{id} with body: {travelDetails:{departureDate, returnDate, destination, isDayTrip:false, isForeignTravel:false, isCompensationFromRates:true}}
4. GET /travelExpense/costCategory → get cost category IDs (Fly, Hotell, Taxi etc.)
5. GET /travelExpense/paymentType → get paymentType ID (REQUIRED for costs — do NOT skip this!)
6. POST /travelExpense/cost for EACH expense: {travelExpense:{id}, costCategory:{id}, paymentType:{id}, amountCurrencyIncVat(NOT amount), date} — POST costs ONE AT A TIME (not parallel) to avoid RevisionException
7. For per diem: GET /travelExpense/rateCategory?type=PER_DIEM&isValidDomestic=true&dateFrom=X&dateTo=Y → get rateCategory ID
8. POST /travelExpense/perDiemCompensation {travelExpense:{id}, rateCategory:{id}, location:"DOMESTIC", overnightAccommodation:"NONE", count:DAYS, rate:DAILY_RATE} — use "HOTEL" only if prompt mentions hotel/overnight stay, otherwise "NONE". rate field is REQUIRED (daily rate from prompt).

## Correction Vouchers
To fix errors: create new voucher with reversed postings (negated amounts) + correct postings
Posted vouchers CANNOT be deleted — always use correction vouchers
CRITICAL: When reversing a posting, COPY ALL fields from the original:
- account:{id} — same account
- supplier:{id} — MUST include if original had supplier (otherwise "Leverandør mangler" error)
- customer:{id} — MUST include if original had customer
- vatType:{id} — same VAT type as original
- amountGross/amountGrossCurrency — NEGATED (opposite sign)
Example: if original was {account:{id:100}, supplier:{id:50}, amountGross:5000}, correction must be {account:{id:100}, supplier:{id:50}, amountGross:-5000}

## Batch Endpoints
POST /product/list, /department/list, /ledger/account/list, /order/orderline/list — for multiple items in one call

## Accounting Dimensions
POST /ledger/accountingDimensionName {dimensionName(NOT name)}
POST /ledger/accountingDimensionValue {displayName(NOT name), dimensionIndex}

## Linking Dimensions to Voucher Postings
Use field: freeAccountingDimension1:{id:VALUE_ID} on each posting
- VALUE_ID comes from POST /ledger/accountingDimensionValue response
- Do NOT use: dimension1, accountingDimension1, customDimension1 — these field names don't exist
