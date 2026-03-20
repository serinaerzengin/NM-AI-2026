# order

Tripletex API endpoints for managing order resources.

## Endpoints

### `GET` /order

Find orders corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `number`: Equals
- `customerId`: List of IDs
- `orderDateFrom` (required): From and including
- `orderDateTo` (required): To and excluding
- `deliveryComment`: Containing
- `isClosed`: Equals
- `isSubscription`: Equals
- `from`: From index
- `count`: Number of elements to return

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

### `POST` /order

Create order.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
  "contact": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url"
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
    "displayName": "<displayName>",
    "receiverEmail": "<receiverEmail>",
    "overdueNoticeEmail": "<overdueNoticeEmail>",
    "number": "<number>",
    "reference": "<reference>"
  }
}
```

### `PUT` /order/:invoiceMultipleOrders

[BETA] Charges a single customer invoice from multiple orders. The orders must be to the same customer, currency, due date, receiver email, attn. and smsNotificationNumber

**Query parameters:**
- `id` (required): List of Order IDs - to the same customer, separated by comma.
- `invoiceDate` (required): The invoice date
- `sendToCustomer`: Send invoice to customer
- `createBackorders`: Create a backorder for all any orders that delivers less than ordered amount

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

### `POST` /order/list

[BETA] Create multiple Orders with OrderLines. Max 100 at a time.

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

### `GET` /order/orderConfirmation/{orderId}/pdf

Get PDF representation of order by ID.

**Query parameters:**
- `download`: Equals

### `GET` /order/orderGroup

Find orderGroups corresponding with sent data.

**Query parameters:**
- `ids`: List of IDs
- `orderIds`: List of IDs
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

### `PUT` /order/orderGroup

[Beta] Put orderGroup.

**Query parameters:**
- `OrderLineIds`: Deprecated. Put order lines in the dto instead.
- `removeExistingOrderLines`: Deprecated. Should existing orderLines be removed from this orderGroup. This will always happen if o

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "order": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "displayName": "<displayName>",
    "receiverEmail": "<receiverEmail>",
    "overdueNoticeEmail": "<overdueNoticeEmail>",
    "number": "<number>",
    "reference": "<reference>"
  },
  "title": "<title>",
  "comment": "<comment>",
  "sortIndex": 0,
  "orderLines": [
    "..."
  ]
}
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
    "title": "<title>",
    "comment": "<comment>",
    "sortIndex": 0,
    "orderLines": [
      "..."
    ]
  }
}
```

### `POST` /order/orderGroup

[Beta] Post orderGroup.

**Query parameters:**
- `orderLineIds`: Deprecated. Put order lines in the dto instead.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "order": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "displayName": "<displayName>",
    "receiverEmail": "<receiverEmail>",
    "overdueNoticeEmail": "<overdueNoticeEmail>",
    "number": "<number>",
    "reference": "<reference>"
  },
  "title": "<title>",
  "comment": "<comment>",
  "sortIndex": 0,
  "orderLines": [
    "..."
  ]
}
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
    "title": "<title>",
    "comment": "<comment>",
    "sortIndex": 0,
    "orderLines": [
      "..."
    ]
  }
}
```

### `GET` /order/orderGroup/{id}

Get orderGroup by ID. A orderGroup is a way to group orderLines, and add comments and subtotals

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
    "title": "<title>",
    "comment": "<comment>",
    "sortIndex": 0,
    "orderLines": [
      "..."
    ]
  }
}
```

### `DELETE` /order/orderGroup/{id}

Delete orderGroup by ID.

### `POST` /order/orderline

Create order line. When creating several order lines, use /list for better performance.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "product": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "number": "<number>",
    "displayNumber": "<displayNumber>",
    "description": "<description>",
    "orderLineDescription": "<orderLineDescription>",
    "ean": "<ean>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>"
  },
  "inventory": {
    "id": 0,
    "version": 0,
    "chan
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
    "description": "<description>",
    "displayName": "<displayName>",
    "count": 0.0,
    "unitCostCurrency": 0.0,
    "unitPriceExcludingVatCurrency": 0.0
  }
}
```

### `POST` /order/orderline/list

Create multiple order lines.

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

### `GET` /order/orderline/orderLineTemplate

[BETA] Get order line template from order and product

**Query parameters:**
- `orderId` (required): Equals
- `productId` (required): Equals
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
    "count": 0.0,
    "unitCostCurrency": 0.0,
    "unitPriceExcludingVatCurrency": 0.0
  }
}
```

### `GET` /order/orderline/{id}

Get order line by ID.

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
    "count": 0.0,
    "unitCostCurrency": 0.0,
    "unitPriceExcludingVatCurrency": 0.0
  }
}
```

### `PUT` /order/orderline/{id}

[BETA] Put order line

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "product": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "number": "<number>",
    "displayNumber": "<displayNumber>",
    "description": "<description>",
    "orderLineDescription": "<orderLineDescription>",
    "ean": "<ean>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>"
  },
  "inventory": {
    "id": 0,
    "version": 0,
    "chan
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
    "description": "<description>",
    "displayName": "<displayName>",
    "count": 0.0,
    "unitCostCurrency": 0.0,
    "unitPriceExcludingVatCurrency": 0.0
  }
}
```

### `DELETE` /order/orderline/{id}

[BETA] Delete order line by ID.

### `PUT` /order/orderline/{id}/:pickLine

[BETA] Pick order line. This is only available for customers who have Logistics and who activated the available inventory functionality.

**Query parameters:**
- `inventoryId`: Optional inventory id. If no inventory is sent, default inventory will be used.
- `inventoryLocationId`: Optional inventory location id
- `pickDate`: Optional pick date. If not sent, current date will be used.

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
    "count": 0.0,
    "unitCostCurrency": 0.0,
    "unitPriceExcludingVatCurrency": 0.0
  }
}
```

### `PUT` /order/orderline/{id}/:unpickLine

[BETA] Unpick order line.This is only available for customers who have Logistics and who activated the available inventory functionality.

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
    "count": 0.0,
    "unitCostCurrency": 0.0,
    "unitPriceExcludingVatCurrency": 0.0
  }
}
```

### `GET` /order/packingNote/{orderId}/pdf

Get PDF representation of packing note by ID.

**Query parameters:**
- `type`: Type of packing note to download.
- `download`: Equals

### `PUT` /order/sendInvoicePreview/{orderId}

Send Invoice Preview to customer by email.

**Query parameters:**
- `email`: email
- `message`: message
- `saveAsDefault`: saveAsDefault

### `PUT` /order/sendOrderConfirmation/{orderId}

Send Order Confirmation to customer by email.

**Query parameters:**
- `email`: email
- `message`: message
- `saveAsDefault`: saveAsDefault

### `PUT` /order/sendPackingNote/{orderId}

Send Packing Note to customer by email.

**Query parameters:**
- `email`: email
- `message`: message
- `saveAsDefault`: saveAsDefault
- `type`: Type of packing note to send.

### `GET` /order/{id}

Get order by ID.

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
    "displayName": "<displayName>",
    "receiverEmail": "<receiverEmail>",
    "overdueNoticeEmail": "<overdueNoticeEmail>",
    "number": "<number>",
    "reference": "<reference>"
  }
}
```

### `PUT` /order/{id}

Update order.

**Query parameters:**
- `updateLinesAndGroups`: Should order lines and order groups be saved and not included lines/groups be removed? Only applies 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
  "contact": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url"
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
    "displayName": "<displayName>",
    "receiverEmail": "<receiverEmail>",
    "overdueNoticeEmail": "<overdueNoticeEmail>",
    "number": "<number>",
    "reference": "<reference>"
  }
}
```

### `DELETE` /order/{id}

Delete order.

### `PUT` /order/{id}/:approveSubscriptionInvoice

To create a subscription invoice, first create a order with the subscription enabled, then approve it with this method. This approves the order for subscription invoicing.

**Query parameters:**
- `invoiceDate` (required): The approval date for the subscription.

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

### `PUT` /order/{id}/:attach

Attach document to specified order ID.

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
    "fileName": "<fileName>",
    "size": 0,
    "archiveDate": "<archiveDate>",
    "mimeType": "<mimeType>"
  }
}
```

### `PUT` /order/{id}/:invoice

Create new invoice or subscription invoice from order.

**Query parameters:**
- `invoiceDate` (required): The invoice date
- `sendToCustomer`: Send invoice to customer
- `sendType`: Send type used for sending the invoice
- `paymentTypeId`: Payment type to register prepayment of the invoice. paymentTypeId and paidAmount are optional, but b
- `paidAmount`: Paid amount to register prepayment of the invoice, in invoice currency. paymentTypeId and paidAmount
- `paidAmountAccountCurrency`: Amount paid in payment type currency
- `paymentTypeIdRestAmount`: Payment type of rest amount. It is possible to have two prepaid payments when invoicing. If paymentT
- `paidAmountAccountCurrencyRest`: Amount rest in payment type currency
- `createOnAccount`: Create on account(a konto)
- `amountOnAccount`: Amount on account

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

### `PUT` /order/{id}/:unApproveSubscriptionInvoice

Unapproves the order for subscription invoicing.

## Common usage patterns

```bash
# Create order (needed before invoice)
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/order" -d '{"customer":{"id":123},"deliveryDate":"2026-03-19","orderDate":"2026-03-19"}'

# Add order line
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/order/orderline" -d '{"order":{"id":456},"product":{"id":789},"count":1}'
```
