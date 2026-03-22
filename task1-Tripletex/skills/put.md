# PUT Patterns

## Action Endpoints (use QUERY PARAMS, not body)
- PUT /order/{id}/:invoice?invoiceDate=DATE — create invoice from order
- PUT /invoice/{id}/:payment?paymentDate=DATE&paymentTypeId=ID&paidAmount=AMOUNT — register payment (paidAmount includes VAT, use negative for reversal)
- PUT /invoice/{id}/:createCreditNote?date=DATE — create credit note
- PUT /invoice/{id}/:send?sendType=EMAIL — send invoice by email

## Travel Expense
- PUT /travelExpense/{id}/convert — REQUIRED before setting travelDetails or per diem (converts type=1 to type=0)
- PUT /travelExpense/{id} — set travelDetails object (only works on type=0!):
  {travelDetails: {departureDate, returnDate, destination, isDayTrip:false, isForeignTravel:false, isCompensationFromRates:true}}
  WARNING: travelDetails is silently IGNORED on type=1 — must convert first!

## Foreign Currency Payment
After registering payment on a foreign currency invoice:
1. Calculate: originalNOK = foreignAmount × oldRate, paidNOK = foreignAmount × newRate
2. difference = paidNOK - originalNOK
3. If difference > 0 (gain/agio): POST voucher with debit 1920(Bank) + credit 8060(Valutagevinst)
4. If difference < 0 (loss/disagio): POST voucher with debit 8160(Valutatap) + credit 1920(Bank)

## Project Invoicing
There is NO /project/:invoice endpoint. To invoice from a project:
1. Create a product for the project work
2. POST /order {customer:{id}, orderDate, deliveryDate, orderLines:[{product:{id}, count}]}
3. PUT /order/{id}/:invoice?invoiceDate=DATE → returns the INVOICE object
4. Extract invoice ID from response, use for payment: PUT /invoice/{id}/:payment?paymentDate&paymentTypeId&paidAmount

## Project Activities
POST /project/projectActivity {project:{id}, activity:{name, activityType:"PROJECT_SPECIFIC_ACTIVITY"}}
Do NOT use POST /activity for project-specific activities — it will fail.

## Updates
- PUT /employee/{id} — update employee (e.g. set dateOfBirth)
- PUT /employee/employment/{id} — update employment (e.g. link division)
- PUT /ledger/account/{id} — update account (e.g. set bankAccountNumber)
