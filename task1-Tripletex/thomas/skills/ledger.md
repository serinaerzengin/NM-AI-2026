# ledger

Tripletex API endpoints for managing ledger resources.

## Endpoints

### `GET` /ledger

Get ledger (hovedbok).

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
- `openPostings`: Deprecated
- `accountId`: Element ID for filtering
- `supplierId`: Element ID for filtering
- `customerId`: Element ID for filtering
- `employeeId`: Element ID for filtering
- `departmentId`: Element ID for filtering
- `projectId`: Element ID for filtering
- `productId`: Element ID for filtering

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

### `GET` /ledger/account

Find accounts corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `number`: List of IDs
- `isBankAccount`: Equals
- `isInactive`: Equals
- `isApplicableForSupplierInvoice`: Equals
- `ledgerType`: Ledger type
- `isBalanceAccount`: Balance account
- `saftCode`: SAF-T code
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

### `POST` /ledger/account

Create a new account.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "number": 0,
  "numberPretty": "<numberPretty>",
  "name": "<name>",
  "description": "<description>",
  "type": "<type>",
  "legalVatTypes": [
    "..."
  ],
  "ledgerType": "<ledgerType>",
  "balanceGroup": "<balanceGroup>"
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
    "number": 0,
    "numberPretty": "<numberPretty>",
    "name": "<name>",
    "description": "<description>",
    "type": "<type>",
    "legalVatTypes": [
      "..."
    ],
    "ledgerType": "<ledgerType>",
    "balanceGroup": "<balanceGroup>"
  }
}
```

### `PUT` /ledger/account/list

Update multiple accounts.

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

### `POST` /ledger/account/list

Create several accounts.

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

### `DELETE` /ledger/account/list

Delete multiple accounts.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /ledger/account/{id}

Get account by ID.

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
    "number": 0,
    "numberPretty": "<numberPretty>",
    "name": "<name>",
    "description": "<description>",
    "type": "<type>",
    "legalVatTypes": [
      "..."
    ],
    "ledgerType": "<ledgerType>",
    "balanceGroup": "<balanceGroup>"
  }
}
```

### `PUT` /ledger/account/{id}

Update account.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "number": 0,
  "numberPretty": "<numberPretty>",
  "name": "<name>",
  "description": "<description>",
  "type": "<type>",
  "legalVatTypes": [
    "..."
  ],
  "ledgerType": "<ledgerType>",
  "balanceGroup": "<balanceGroup>"
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
    "number": 0,
    "numberPretty": "<numberPretty>",
    "name": "<name>",
    "description": "<description>",
    "type": "<type>",
    "legalVatTypes": [
      "..."
    ],
    "ledgerType": "<ledgerType>",
    "balanceGroup": "<balanceGroup>"
  }
}
```

### `DELETE` /ledger/account/{id}

Delete account.

### `GET` /ledger/accountingDimensionName

Get all accounting dimension names.

**Query parameters:**
- `activeOnly`: Whether to only return active dimensions (optional)
- `fields`: Fields to include in response.
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

### `POST` /ledger/accountingDimensionName

Create a new free (aka 'user defined') accounting dimension

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "dimensionName": "<dimensionName>",
  "description": "<description>",
  "dimensionIndex": 0,
  "active": true
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
    "dimensionName": "<dimensionName>",
    "description": "<description>",
    "dimensionIndex": 0,
    "active": true
  }
}
```

### `GET` /ledger/accountingDimensionName/search

Search for accounting dimension names according to criteria.

**Query parameters:**
- `dimensionIndex`: Dimension index to filter by (1, 2, or 3)
- `activeOnly`: Whether to only return active dimensions (optional)
- `onlyDimensionsWithActiveValues`: Whether to only return active dimensions with active values which are shown in voucher registration 
- `fields`: Fields to include in response.
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

### `GET` /ledger/accountingDimensionName/{id}

Get a single accounting dimension name by ID

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
    "dimensionName": "<dimensionName>",
    "description": "<description>",
    "dimensionIndex": 0,
    "active": true
  }
}
```

### `PUT` /ledger/accountingDimensionName/{id}

Update an accounting dimension

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "dimensionName": "<dimensionName>",
  "description": "<description>",
  "dimensionIndex": 0,
  "active": true
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
    "dimensionName": "<dimensionName>",
    "description": "<description>",
    "dimensionIndex": 0,
    "active": true
  }
}
```

### `DELETE` /ledger/accountingDimensionName/{id}

Delete an accounting dimension name by ID

### `POST` /ledger/accountingDimensionValue

Create a new value for one of the free (aka 'user defined') accounting dimensions

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "displayName": "<displayName>",
  "nameAndNumber": "<nameAndNumber>",
  "dimensionIndex": 0,
  "active": true,
  "number": "<number>",
  "showInVoucherRegistration": true,
  "position": 0
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
    "displayName": "<displayName>",
    "nameAndNumber": "<nameAndNumber>",
    "dimensionIndex": 0,
    "active": true,
    "number": "<number>",
    "showInVoucherRegistration": true,
    "position": 0
  }
}
```

### `PUT` /ledger/accountingDimensionValue/list

Update accounting dimension values

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

### `GET` /ledger/accountingDimensionValue/search

Search for accounting dimension values according to criteria.

**Query parameters:**
- `dimensionIndex`: Dimension index to filter by (1, 2, or 3)
- `activeOnly`: Whether to only return active dimension values (optional)
- `showInVoucherRegistration`: Return only values shown in voucher registration (optional)
- `fields`: Fields to include in response.
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

### `GET` /ledger/accountingDimensionValue/{id}

Find accounting dimension values by ID.

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
    "nameAndNumber": "<nameAndNumber>",
    "dimensionIndex": 0,
    "active": true,
    "number": "<number>",
    "showInVoucherRegistration": true,
    "position": 0
  }
}
```

### `DELETE` /ledger/accountingDimensionValue/{id}

Delete an accounting dimension value.  Values that have been used in postings can not be deleted.

### `GET` /ledger/accountingPeriod

Find accounting periods corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `numberFrom`: From and including
- `numberTo`: To and excluding
- `startFrom`: From and including
- `startTo`: To and excluding
- `endFrom`: From and including
- `endTo`: To and excluding
- `count`: Number of elements to return
- `from`: From index
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

### `GET` /ledger/accountingPeriod/{id}

Get accounting period by ID.

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
    "name": "<name>",
    "number": 0,
    "start": "<start>",
    "end": "<end>",
    "isClosed": true,
    "checkLedgerLogEmployeeName": "<checkLedgerLogEmployeeName>",
    "checkLedgerLogEmployeePictureId": 0,
    "checkLedgerLogTime": "<checkLedgerLogTime>"
  }
}
```

### `GET` /ledger/annualAccount

Find annual accounts corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `yearFrom`: From and including
- `yearTo`: To and excluding
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

### `GET` /ledger/annualAccount/{id}

Get annual account by ID.

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
    "year": 0,
    "start": "<start>",
    "end": "<end>"
  }
}
```

### `GET` /ledger/closeGroup

Find close groups corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `dateFrom` (required): From and including
- `dateTo` (required): To and excluding
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

### `GET` /ledger/closeGroup/{id}

Get close group by ID.

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
    "date": "<date>",
    "postings": [
      "..."
    ]
  }
}
```

### `GET` /ledger/openPost

Find open posts corresponding with sent data.

**Query parameters:**
- `date` (required): Invoice date. Format is yyyy-MM-dd (to and excl.).
- `accountId`: Element ID for filtering
- `supplierId`: Element ID for filtering
- `customerId`: Element ID for filtering
- `employeeId`: Element ID for filtering
- `departmentId`: Element ID for filtering
- `projectId`: Element ID for filtering
- `productId`: Element ID for filtering
- `accountingDimensionValue1Id`: Id of first free accounting dimension.
- `accountingDimensionValue2Id`: Id of second free accounting dimension.

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

### `GET` /ledger/paymentTypeOut

[BETA] Gets payment types for outgoing payments

**Query parameters:**
- `id`: List of IDs
- `description`: Containing
- `isInactive`: Equals
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

### `POST` /ledger/paymentTypeOut

[BETA] Create new payment type for outgoing payments

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "description": "<description>",
  "isBruttoWageDeduction": true,
  "creditAccount": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "number": 0,
    "numberPretty": "<numberPretty>",
    "name": "<name>",
    "description": "<description>",
    "type": "<type>",
    "legalVatTypes": [
      "..."
    ],
    "ledgerType": "<ledgerType>",
    "balanceGroup": "<balanceGroup>"

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
    "isBruttoWageDeduction": true,
    "showIncomingInvoice": true,
    "showWagePayment": true,
    "showVatReturns": true,
    "showWagePeriodTransaction": true,
    "requiresSeparateVoucher": true
  }
}
```

### `PUT` /ledger/paymentTypeOut/list

[BETA] Update multiple payment types for outgoing payments at once

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

### `POST` /ledger/paymentTypeOut/list

[BETA] Create multiple payment types for outgoing payments at once

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

### `GET` /ledger/paymentTypeOut/{id}

[BETA] Get payment type for outgoing payments by ID.

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
    "isBruttoWageDeduction": true,
    "showIncomingInvoice": true,
    "showWagePayment": true,
    "showVatReturns": true,
    "showWagePeriodTransaction": true,
    "requiresSeparateVoucher": true
  }
}
```

### `PUT` /ledger/paymentTypeOut/{id}

[BETA] Update existing payment type for outgoing payments

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "description": "<description>",
  "isBruttoWageDeduction": true,
  "creditAccount": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "number": 0,
    "numberPretty": "<numberPretty>",
    "name": "<name>",
    "description": "<description>",
    "type": "<type>",
    "legalVatTypes": [
      "..."
    ],
    "ledgerType": "<ledgerType>",
    "balanceGroup": "<balanceGroup>"

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
    "isBruttoWageDeduction": true,
    "showIncomingInvoice": true,
    "showWagePayment": true,
    "showVatReturns": true,
    "showWagePeriodTransaction": true,
    "requiresSeparateVoucher": true
  }
}
```

### `DELETE` /ledger/paymentTypeOut/{id}

[BETA] Delete payment type for outgoing payments by ID.

### `GET` /ledger/posting

Find postings corresponding with sent data.

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
- `openPostings`: Deprecated
- `accountId`: Element ID for filtering
- `supplierId`: Element ID for filtering
- `customerId`: Element ID for filtering
- `employeeId`: Element ID for filtering
- `departmentId`: Element ID for filtering
- `projectId`: Element ID for filtering
- `productId`: Element ID for filtering

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

### `PUT` /ledger/posting/:closePostings

Close postings.

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

### `GET` /ledger/posting/openPost

Find open posts corresponding with sent data.

**Query parameters:**
- `date` (required): Invoice date. Format is yyyy-MM-dd (to and excl.).
- `accountId`: Element ID for filtering
- `supplierId`: Element ID for filtering
- `customerId`: Element ID for filtering
- `employeeId`: Element ID for filtering
- `departmentId`: Element ID for filtering
- `projectId`: Element ID for filtering
- `productId`: Element ID for filtering
- `accountNumberFrom`: Element ID for filtering
- `accountNumberTo`: Element ID for filtering

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

### `GET` /ledger/posting/{id}

Find postings by ID.

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
    "date": "<date>",
    "description": "<description>",
    "amortizationStartDate": "<amortizationStartDate>",
    "amortizationEndDate": "<amortizationEndDate>"
  }
}
```

### `GET` /ledger/postingByDate

Get postings by date range with pagination. Returns the same PostingDTO as /ledger/posting. Simplified endpoint for better performance. Fields and Changes are not supported. Token must have access to all vouchers in the company, otherwise a validation error is returned. If access control for salary information is activated, the token must have access to salary information as well.

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
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

### `GET` /ledger/postingRules

Get posting rules for current company.  The posting rules defined which accounts from the chart of accounts that are used for postings when the system creates postings.

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
    "vatPerDepartment": true,
    "multipleIndustries": true,
    "defaultBusinessActivityTypeId": 0
  }
}
```

### `GET` /ledger/vatSettings

Get VAT settings for the logged in company.

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
    "vatRegistrationStatus": "<vatRegistrationStatus>"
  }
}
```

### `PUT` /ledger/vatSettings

Update VAT settings for the logged in company.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "vatRegistrationStatus": "<vatRegistrationStatus>"
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
    "vatRegistrationStatus": "<vatRegistrationStatus>"
  }
}
```

### `GET` /ledger/vatType

Find vat types corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `number`: List of IDs
- `typeOfVat`: Type of VAT
- `vatDate`: yyyy-MM-dd. Defaults to today. Note that this is only used in combination with typeOfVat-parameter. 
- `shouldIncludeSpecificationTypes`: Equals
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

### `PUT` /ledger/vatType/createRelativeVatType

Create a new relative VAT Type. These are used if the company has 'forholdsmessig fradrag for inngående MVA'.

**Query parameters:**
- `name` (required): VAT type name, max 8 characters.
- `vatTypeId` (required): VAT type ID. The relative VAT type will behave like this VAT type, except for the basis for calculat
- `percentage` (required): Basis percentage. This percentage will be multiplied with the transaction amount to find the amount 

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
    "name": "<name>",
    "number": "<number>",
    "displayName": "<displayName>",
    "percentage": 0.0,
    "deductionPercentage": 0.0
  }
}
```

### `GET` /ledger/vatType/{id}

Get vat type by ID.

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
    "name": "<name>",
    "number": "<number>",
    "displayName": "<displayName>",
    "percentage": 0.0,
    "deductionPercentage": 0.0
  }
}
```

### `GET` /ledger/voucher

Find vouchers corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `number`: List of IDs
- `numberFrom`: From and including
- `numberTo`: To and excluding
- `typeId`: List of IDs
- `dateFrom` (required): From and including
- `dateTo` (required): To and excluding
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
  ],
  "totalNumberOfPostings": 0
}
```

### `POST` /ledger/voucher

Add new voucher. IMPORTANT: Also creates postings. Only the gross amounts will be used. Amounts should be rounded to 2 decimals.

**Query parameters:**
- `sendToLedger`: Should the voucher be sent to ledger? Requires the "Advanced Voucher" permission.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "date": "<date>",
  "number": 0,
  "tempNumber": 0,
  "year": 0,
  "description": "<description>",
  "voucherType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>"
  },
  "reverseVoucher": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "date": "<date>",
    "number": 0,
    "t
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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `GET` /ledger/voucher/>externalVoucherNumber

Find vouchers based on the external voucher number.

**Query parameters:**
- `externalVoucherNumber`: The external voucher number, when voucher is created from import.
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

### `GET` /ledger/voucher/>nonPosted

Find non-posted vouchers.

**Query parameters:**
- `dateFrom`: From and including
- `dateTo`: To and excluding
- `includeNonApproved` (required): Include non-approved vouchers in the result.
- `changedSince`: Only return elements that have changed since this date and time
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

### `GET` /ledger/voucher/>voucherReception

Find vouchers in voucher reception.

**Query parameters:**
- `dateFrom`: From and including
- `dateTo`: To and excluding
- `searchText`: Search
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

### `PUT` /ledger/voucher/historical/:closePostings

[BETA] Close postings.

**Query parameters:**
- `postingIds`: [Deprecated] List of Posting IDs to close separated by comma. The postings should have the same cust

**Request body example:**
```json
"<string>"
```

### `PUT` /ledger/voucher/historical/:reverseHistoricalVouchers

[BETA] Deletes all historical vouchers. Requires the "All vouchers" and "Advanced Voucher" permissions.

### `POST` /ledger/voucher/historical/employee

[BETA] Create one employee, based on import from external system. Validation is less strict, ie. employee department isn't required.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "firstName": "<firstName>",
  "lastName": "<lastName>",
  "displayName": "<displayName>",
  "employeeNumber": "<employeeNumber>",
  "dateOfBirth": "<dateOfBirth>",
  "email": "<email>",
  "phoneNumberMobileCountry": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
    "isoAlpha2Code": "<isoAlpha2Code>",
    "isoAlpha3Code
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
    "firstName": "<firstName>",
    "lastName": "<lastName>",
    "displayName": "<displayName>",
    "employeeNumber": "<employeeNumber>",
    "dateOfBirth": "<dateOfBirth>",
    "email": "<email>",
    "phoneNumberMobile": "<phoneNumberMobile>"
  }
}
```

### `POST` /ledger/voucher/historical/historical

API endpoint for creating historical vouchers. These are vouchers created outside Tripletex, and should be from closed accounting years. The intended usage is to get access to historical transcations in Tripletex. Also creates postings. All amount fields in postings will be used. VAT postings must be included, these are not generated automatically like they are for normal vouchers in Tripletex. Requires the \"All vouchers\" and \"Advanced Voucher\" permissions.

**Query parameters:**
- `comment`: Import comment, include the name and version of the source system.
- `useCustomNumberSeries`: Use custom number series (true), or use default number series for historical vouchers (false).

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

### `POST` /ledger/voucher/historical/{voucherId}/attachment

Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). Valid document formats are PDF, PNG, JPEG and TIFF. Non PDF formats will be converted to PDF. Send as multipart form.

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
    "date": "<date>",
    "externalVoucherNumber": "<externalVoucherNumber>",
    "number": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `POST` /ledger/voucher/importDocument

Upload a document to create one or more vouchers. Valid document formats are PDF, PNG, JPEG and TIFF. EHF/XML is possible with agreement with Tripletex. Send as multipart form.

**Query parameters:**
- `split`: If the document consists of several pages, should the document be split into one voucher per page?

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

### `POST` /ledger/voucher/importGbat10

Import GBAT10. Send as multipart form.

### `PUT` /ledger/voucher/list

Update multiple vouchers. Postings with guiRow==0 will be deleted and regenerated.

**Query parameters:**
- `sendToLedger`: Should the voucher be sent to ledger? Requires the "Advanced Voucher" permission.

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

### `GET` /ledger/voucher/openingBalance

[BETA] Get the voucher for the opening balance.

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `POST` /ledger/voucher/openingBalance

[BETA] Add an opening balance on the given date.  All movements before this date will be 'zeroed out' in a separate correction voucher. The opening balance must have the first day of a month as the date, and it's also recommended to have the first day of the year as the date. If the postings provided don't balance the voucher, the difference will automatically be posted to a help account

**Query parameters:**
- `fields`: Fields filter pattern

**Request body example:**
```json
{
  "voucherDate": "<voucherDate>",
  "balancePostings": [
    "..."
  ],
  "customerPostings": [
    "..."
  ],
  "supplierPostings": [
    "..."
  ],
  "employeePostings": [
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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `DELETE` /ledger/voucher/openingBalance

[BETA] Delete the opening balance. The correction voucher will also be deleted

### `GET` /ledger/voucher/openingBalance/>correctionVoucher

[BETA] Get the correction voucher for the opening balance.

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `GET` /ledger/voucher/{id}

Get voucher by ID.

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `PUT` /ledger/voucher/{id}

Update voucher. Postings with guiRow==0 will be deleted and regenerated.

**Query parameters:**
- `sendToLedger`: Should the voucher be sent to ledger? Requires the "Advanced Voucher" permission.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "date": "<date>",
  "number": 0,
  "tempNumber": 0,
  "year": 0,
  "description": "<description>",
  "voucherType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>"
  },
  "reverseVoucher": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "date": "<date>",
    "number": 0,
    "t
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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `DELETE` /ledger/voucher/{id}

Delete voucher by ID.

### `PUT` /ledger/voucher/{id}/:reverse

Reverses the voucher, and returns the reversed voucher. Supports reversing most voucher types, except salary transactions.

**Query parameters:**
- `date` (required): Reverse voucher date

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `PUT` /ledger/voucher/{id}/:sendToInbox

Send voucher to inbox.

**Query parameters:**
- `version`: Version of voucher that should be sent to inbox.
- `comment`: Description of why the voucher was rejected. This parameter is only used if the approval feature is 

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `PUT` /ledger/voucher/{id}/:sendToLedger

Send voucher to ledger.

**Query parameters:**
- `version`: Version of voucher that should be sent to ledger.
- `number`: Voucher number to use. If omitted or 0 the system will assign the number.

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `GET` /ledger/voucher/{id}/options

Returns a data structure containing meta information about operations that are available for this voucher. Currently only implemented for DELETE: It is possible to check if the voucher is deletable.

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {}
}
```

### `POST` /ledger/voucher/{voucherId}/attachment

Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). Valid document formats are PDF, PNG, JPEG and TIFF. Non PDF formats will be converted to PDF. Send as multipart form.

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
    "date": "<date>",
    "number": 0,
    "tempNumber": 0,
    "year": 0,
    "description": "<description>",
    "postings": [
      "..."
    ]
  }
}
```

### `DELETE` /ledger/voucher/{voucherId}/attachment

Delete attachment.

**Query parameters:**
- `version`: Version of voucher containing the attachment to delete.
- `sendToInbox`: Should the attachment be sent to inbox rather than deleted?
- `split`: If sendToInbox is true, should the attachment be split into one voucher per page?

### `GET` /ledger/voucher/{voucherId}/pdf

Get PDF representation of voucher by ID.

### `POST` /ledger/voucher/{voucherId}/pdf/{fileName}

[DEPRECATED] Use POST ledger/voucher/{voucherId}/attachment instead.

### `GET` /ledger/voucherType

Find voucher types corresponding with sent data.

**Query parameters:**
- `name`: Containing
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

### `GET` /ledger/voucherType/{id}

Get voucher type by ID.

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
    "name": "<name>",
    "displayName": "<displayName>"
  }
}
```

## Common usage patterns

```bash
# List accounts
curl -u "0:$TOKEN" "$URL/ledger/account?fields=id,number,name"

# Create voucher
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/ledger/voucher" -d '{"date":"2026-03-19","description":"Test","postings":[...]}'

# Reverse voucher
curl -X PUT -u "0:$TOKEN" "$URL/ledger/voucher/123/:reverse"
```
