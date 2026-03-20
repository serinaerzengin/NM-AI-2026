# invoice

Tripletex API endpoints for managing invoice resources.

## Endpoints

### `GET` /invoice

Find invoices corresponding with sent data. Includes charged outgoing invoices only.

**Query parameters:**
- `id`: List of IDs
- `invoiceDateFrom` (required): From and including
- `invoiceDateTo` (required): To and excluding
- `invoiceNumber`: Equals
- `kid`: Equals
- `voucherId`: List of IDs
- `customerId`: Equals
- `from`: From index
- `count`: Number of elements to return
- `sorting`: Sorting pattern

**Response example:**
```json
{
  "fullResultSize": 0,
  "from": 0,
  "count": 0,
  "versionDigest": "<versionDigest>",
  "values": [
    "..."
  ]
}
```

### `POST` /invoice

Create invoice. Related Order and OrderLines can be created first, or included as new objects inside the Invoice.

**Query parameters:**
- `sendToCustomer`: Equals
- `paymentTypeId`: Payment type to register prepayment of the invoice. paymentTypeId and paidAmount are optional, but b
- `paidAmount`: Paid amount to register prepayment of the invoice, in invoice currency. paymentTypeId and paidAmount

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "invoiceNumber": 0,
  "invoiceDate": "<invoiceDate>",
  "customer": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "organizationNumber": "<organizationNumber>",
    "globalLocationNumber": 0,
    "supplierNumber": 0,
    "customerNumber": 0,
    "isSupplier": true,
    "isCustomer": true,
    "isInactive": true
  },
  "creditedInvoice": 0,
  "isCredit
```

**Response example:**
```json
{
  "value": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "invoiceNumber": 0,
    "invoiceDate": "<invoiceDate>",
    "creditedInvoice": 0,
    "isCredited": true,
    "invoiceDueDate": "<invoiceDueDate>",
    "kid": "<kid>",
    "invoiceComment": "<invoiceComment>"
  }
}
```

### `GET` /invoice/details

Find ProjectInvoiceDetails corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `invoiceDateFrom` (required): From and including
- `invoiceDateTo` (required): To and excluding
- `from`: From index
- `count`: Number of elements to return
- `sorting`: Sorting pattern
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "fullResultSize": 0,
  "from": 0,
  "count": 0,
  "versionDigest": "<versionDigest>",
  "values": [
    "..."
  ]
}
```

### `GET` /invoice/details/{id}

Get ProjectInvoiceDetails by ID.

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "feeAmount": 0.0,
    "feeAmountCurrency": 0.0,
    "markupPercent": 0.0,
    "markupAmount": 0.0,
    "markupAmountCurrency": 0.0,
    "amountOrderLinesAndReinvoicing": 0.0,
    "amountOrderLinesAndReinvoicingCurrency": 0.0
  }
}
```

### `POST` /invoice/list

[BETA] Create multiple invoices. Max 100 at a time.

**Query parameters:**
- `sendToCustomer`: Equals
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "fullResultSize": 0,
  "from": 0,
  "count": 0,
  "versionDigest": "<versionDigest>",
  "values": [
    "..."
  ]
}
```

### `GET` /invoice/paymentType

Find payment type corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `description`: Containing
- `query`: Containing
- `from`: From index
- `count`: Number of elements to return
- `sorting`: Sorting pattern
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "fullResultSize": 0,
  "from": 0,
  "count": 0,
  "versionDigest": "<versionDigest>",
  "values": [
    "..."
  ]
}
```

### `GET` /invoice/paymentType/{id}

Get payment type by ID.

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "description": "<description>",
    "displayName": "<displayName>",
    "sequence": 0
  }
}
```

### `GET` /invoice/{id}

Get invoice by ID.

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "invoiceNumber": 0,
    "invoiceDate": "<invoiceDate>",
    "creditedInvoice": 0,
    "isCredited": true,
    "invoiceDueDate": "<invoiceDueDate>",
    "kid": "<kid>",
    "invoiceComment": "<invoiceComment>"
  }
}
```

### `PUT` /invoice/{id}/:createCreditNote

Creates a new Invoice representing a credit memo that nullifies the given invoice. Updates this invoice and any pre-existing inverse invoice.

**Query parameters:**
- `date` (required): Credit note date
- `comment`: Comment
- `creditNoteEmail`: The credit note will not be sent if the customer send type is email and this field is empty
- `sendToCustomer`: Equals
- `sendType`: Equals

**Response example:**
```json
{
  "value": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "invoiceNumber": 0,
    "invoiceDate": "<invoiceDate>",
    "creditedInvoice": 0,
    "isCredited": true,
    "invoiceDueDate": "<invoiceDueDate>",
    "kid": "<kid>",
    "invoiceComment": "<invoiceComment>"
  }
}
```

### `PUT` /invoice/{id}/:createReminder

Create invoice reminder and sends it by the given dispatch type. Supports the reminder types SOFT_REMINDER, REMINDER and NOTICE_OF_DEBT_COLLECTION. DispatchType NETS_PRINT must have type NOTICE_OF_DEBT_COLLECTION. SMS and NETS_PRINT must be activated prior to usage in the API.

**Query parameters:**
- `type` (required): type
- `date` (required): yyyy-MM-dd. Defaults to today.
- `includeCharge`: Equals
- `includeInterest`: Equals
- `dispatchType`: dispatchType
- `dispatchTypes`: List of dispatch types (comma separated enum values)
- `smsNumber`: SMS number (must be a valid Norwegian telephone number)
- `email`: Email address to send the reminder to. (Defaults to to the same email list as the invoice if not pro
- `address`: Address to send the reminder to. (Defaults to the customer address if not provided)
- `postalCode`: Postal code to send the reminder to (Defaults to the customer postal code if not provided)

**Response example:**
```json
{
  "value": 0
}
```

### `PUT` /invoice/{id}/:payment

Update invoice. The invoice is updated with payment information. The amount is in the invoice’s currency.

**Query parameters:**
- `paymentDate` (required): Payment date
- `paymentTypeId` (required): PaymentType id
- `paidAmount` (required): Amount paid by the customer in the currency determined by the account of the paymentType
- `paidAmountCurrency`: Amount paid by customer in the invoice currency. Optional, but required for invoices in alternate cu

**Response example:**
```json
{
  "value": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "invoiceNumber": 0,
    "invoiceDate": "<invoiceDate>",
    "creditedInvoice": 0,
    "isCredited": true,
    "invoiceDueDate": "<invoiceDueDate>",
    "kid": "<kid>",
    "invoiceComment": "<invoiceComment>"
  }
}
```

### `PUT` /invoice/{id}/:send

Send invoice by ID and sendType. Optionally override email recipient.

**Query parameters:**
- `sendType` (required): SendType
- `overrideEmailAddress`: Will override email address if sendType = EMAIL

### `GET` /invoice/{invoiceId}/pdf

Get invoice document by invoice ID.

**Query parameters:**
- `download`: Equals

## Common usage patterns

```bash
# List invoices
curl -u "0:$TOKEN" "$URL/invoice?fields=id,invoiceNumber,customer(*)"

# Create invoice (needs customer + order first)
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/invoice" -d '{"invoiceDate":"2026-03-19","invoiceDueDate":"2026-04-19","customer":{"id":123},"orders":[{"id":456}]}'

# Register payment on invoice
curl -X PUT -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/invoice/789/:payment" -d '{"paymentDate":"2026-03-19","paymentTypeId":1,"amount":1000}'
```
