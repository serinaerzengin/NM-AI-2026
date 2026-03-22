# DELETE Patterns

## Travel Expense
- DELETE /travelExpense/{id} — delete a travel expense report

## Vouchers
- DELETE /ledger/voucher/{id} — ONLY works on draft/unposted vouchers
- Posted vouchers CANNOT be deleted → create correction voucher instead (reverse postings with negated amounts)

## Invoices
- Cannot delete invoices → use credit note: PUT /invoice/{id}/:createCreditNote?date=DATE

## Payments
- Cannot delete payments → register negative payment: PUT /invoice/{id}/:payment with negative paidAmount
