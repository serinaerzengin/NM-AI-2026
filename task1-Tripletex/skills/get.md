# GET Patterns

## Entity Lookups
- /customer?organizationNumber=X — find customer
- /supplier?organizationNumber=X — find supplier
- /employee?email=X — find employee
- /product?name=X or ?number=X — find product

## Account Lookups (ALWAYS batch in one call)
- /ledger/account?number=1920,2400,6300 — comma-separated, ONE call
- Never look up accounts one at a time

## Required Date Parameters
- /ledger/posting?dateFrom=X&dateTo=Y — ALWAYS required
- /invoice?customerId=X&invoiceDateFrom=2020-01-01&invoiceDateTo=2030-01-01 — ALWAYS required
- /supplierInvoice?invoiceDateFrom=X&invoiceDateTo=Y — ALWAYS required
- /balanceSheet?dateFrom=X&dateTo=Y — ALWAYS required
- /ledger/openPost?date=X — single date, ALWAYS required
- dateTo is EXCLUSIVE — for same-day use next day (dateFrom=2026-03-21&dateTo=2026-03-22)

## Reference Data
- /ledger/voucherType — voucher types (Norwegian names: Leverandørfaktura, Betaling, Lønnsbilag)
- /invoice/paymentType — payment types for invoice payment
- /salary/type — salary types (Fastlønn, Bonus etc.)
- /ledger/vatType — VAT types
- /department — departments
- /division — divisions (virksomheter)
- /travelExpense/costCategory — cost categories (Fly, Hotell, Taxi)
- /travelExpense/rateCategory?type=PER_DIEM&isValidDomestic=true&dateFrom=X&dateTo=Y — per diem rates (year-specific!)
