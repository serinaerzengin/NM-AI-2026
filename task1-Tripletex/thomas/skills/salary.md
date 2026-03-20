# salary

Tripletex API endpoints for managing salary resources.

## Endpoints

### `GET` /salary/compilation

Find salary compilation by employee.

**Query parameters:**
- `employeeId` (required): Element ID
- `year`: Must be between 1900-2100. Defaults to previous year.
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "employee": 0,
    "year": 0,
    "vacationPayBasis": 0.0,
    "wages": [
      "..."
    ],
    "expenses": [
      "..."
    ],
    "taxDeductions": [
      "..."
    ],
    "mandatoryTaxDeductions": [
      "..."
    ]
  }
}
```

### `GET` /salary/compilation/pdf

Find salary compilation (PDF document) by employee.

**Query parameters:**
- `employeeId` (required): Element ID
- `year`: Must be between 1900-2100. Defaults to previous year.

### `POST` /salary/financeTax/reconciliation/context

Create a financeTax reconciliation context for a customer

**Request body example:**
```json
{
  "customerId": 0,
  "year": 0,
  "term": 0
}
```

**Response example:**
```json
{
  "value": {
    "year": 0,
    "reconciliationId": 0,
    "term": 0
  }
}
```

### `GET` /salary/financeTax/reconciliation/{reconciliationId}/overview

Get finance tax overview for a specific reconciliation term

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "ledgerSum": 15000.0,
    "ameldingSum": 15000.0,
    "taxAuthoritiesSum": 15000.0,
    "discrepancy": 500.0,
    "financeTaxBasisSum": 100000.0,
    "financeTaxSum": 25000.0,
    "ledgerUri": "<ledgerUri>"
  }
}
```

### `GET` /salary/financeTax/reconciliation/{reconciliationId}/paymentsOverview

Get finance tax payment overview from start of year to the current reconciliation term

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "payments": [
      "..."
    ],
    "totalLedgerSum": 0.0,
    "totalAmeldingSum": 0.0,
    "totalPaidAmount": 0.0,
    "totalRestAmount": 0.0
  }
}
```

### `POST` /salary/holidayAllowance/reconciliation/context

Create a holiday allowance reconciliation context for a customer

**Request body example:**
```json
{
  "customerId": 0,
  "year": 0,
  "term": 0
}
```

**Response example:**
```json
{
  "value": {
    "year": 0,
    "reconciliationId": 0,
    "term": 0
  }
}
```

### `GET` /salary/holidayAllowance/reconciliation/{reconciliationId}/holidayAllowanceDetails

Get a holiday allowance details for the current reconciliation term

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "outstandingVacationPayGeneralLedger": 0.0,
    "outstandingVacationPayHolidayAllowanceReport": 0.0,
    "payrollTaxVacationPayGeneralLedger": 0.0,
    "payrollTaxVacationPayHolidayAllowanceReport": 0.0
  }
}
```

### `GET` /salary/holidayAllowance/reconciliation/{reconciliationId}/holidayAllowanceSummary

Salary holiday allowance reconciliation summary

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "rates": [
      "..."
    ],
    "totalCreditPrevYears": 0.0,
    "totalEarnedThisYear": 0.0,
    "totalEarnedAndPaidThisYear": 0.0,
    "totalCreditThisYear": 0.0
  }
}
```

### `POST` /salary/mandatoryDeduction/reconciliation/context

Create a mandatoryDeduction reconciliation context for a customer

**Request body example:**
```json
{
  "customerId": 0,
  "year": 0,
  "term": 0
}
```

**Response example:**
```json
{
  "value": {
    "year": 0,
    "reconciliationId": 0,
    "term": 0
  }
}
```

### `GET` /salary/mandatoryDeduction/reconciliation/{reconciliationId}/overview

Salary mandatory deduction reconciliation overview

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "ledgerSum": 0.0,
    "ameldingSum": 0.0,
    "discrepancy": 0.0,
    "periodOverviews": [
      "..."
    ]
  }
}
```

### `GET` /salary/mandatoryDeduction/reconciliation/{reconciliationId}/paymentsOverview

Get mandatory deduction payments overview from start of year to the current reconciliation term

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "payments": [
      "..."
    ],
    "totalLedgerSum": 0.0,
    "totalAmeldingSum": 0.0,
    "totalPaidAmount": 0.0,
    "totalRestAmount": 0.0
  }
}
```

### `POST` /salary/payrollTax/reconciliation/context

Create a payroll tax reconciliation context for a customer

**Request body example:**
```json
{
  "customerId": 0,
  "year": 0,
  "term": 0
}
```

**Response example:**
```json
{
  "value": {
    "year": 0,
    "reconciliationId": 0,
    "term": 0
  }
}
```

### `GET` /salary/payrollTax/reconciliation/{reconciliationId}/overview

Salary payroll tax reconciliation overview

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "ledgerSum": 15000.0,
    "ameldingSum": 14500.0,
    "discrepancy": 500.0,
    "taxAuthoritiesSum": 15000.0,
    "aggregatedZones": [
      "..."
    ],
    "ledgerUri": "<ledgerUri>"
  }
}
```

### `GET` /salary/payrollTax/reconciliation/{reconciliationId}/paymentsOverview

Get a payroll tax payments from start of year to the current reconciliation term

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "payments": [
      "..."
    ],
    "totalLedgerSum": 0.0,
    "totalAmeldingSum": 0.0,
    "totalPaidAmount": 0.0,
    "totalRestAmount": 0.0
  }
}
```

### `GET` /salary/payslip

Find payslips corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `employeeId`: List of IDs
- `wageTransactionId`: List of IDs
- `activityId`: List of IDs
- `yearFrom`: From and including
- `yearTo`: To and excluding
- `monthFrom`: From and including
- `monthTo`: To and excluding
- `voucherDateFrom`: From and including
- `voucherDateTo`: To and excluding

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

### `GET` /salary/payslip/{id}

Find payslip by ID.

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
    "year": 0,
    "month": 0,
    "specifications": [
      "..."
    ],
    "vacationAllowanceAmount": 0.0,
    "grossAmount": 0.0
  }
}
```

### `GET` /salary/payslip/{id}/pdf

Find payslip (PDF document) by ID.

### `GET` /salary/settings

Get salary settings of logged in company.

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "payrollTaxCalcMethod": "<payrollTaxCalcMethod>"
  }
}
```

### `PUT` /salary/settings

Update settings of logged in company.

**Request body example:**
```json
{
  "municipality": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "number": "<number>",
    "name": "<name>",
    "county": "<county>",
    "payrollTaxZone": "<payrollTaxZone>",
    "displayName": "<displayName>"
  },
  "payrollTaxCalcMethod": "<payrollTaxCalcMethod>"
}
```

**Response example:**
```json
{
  "value": {
    "payrollTaxCalcMethod": "<payrollTaxCalcMethod>"
  }
}
```

### `GET` /salary/settings/holiday

Find holiday settings of current logged in company.

**Query parameters:**
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

### `POST` /salary/settings/holiday

Create a holiday setting of current logged in company.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "year": 0,
  "days": 0.0,
  "vacationPayPercentage1": 0.0,
  "vacationPayPercentage2": 0.0,
  "isMaxPercentage2Amount6G": true
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
    "year": 0,
    "days": 0.0,
    "vacationPayPercentage1": 0.0,
    "vacationPayPercentage2": 0.0,
    "isMaxPercentage2Amount6G": true
  }
}
```

### `PUT` /salary/settings/holiday/list

Update multiple holiday settings of current logged in company.

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

### `POST` /salary/settings/holiday/list

Create multiple holiday settings of current logged in company.

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

### `DELETE` /salary/settings/holiday/list

Delete multiple holiday settings of current logged in company.

**Query parameters:**
- `ids` (required): ID of the elements

### `PUT` /salary/settings/holiday/{id}

Update a holiday setting of current logged in company.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "year": 0,
  "days": 0.0,
  "vacationPayPercentage1": 0.0,
  "vacationPayPercentage2": 0.0,
  "isMaxPercentage2Amount6G": true
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
    "year": 0,
    "days": 0.0,
    "vacationPayPercentage1": 0.0,
    "vacationPayPercentage2": 0.0,
    "isMaxPercentage2Amount6G": true
  }
}
```

### `GET` /salary/settings/pensionScheme

Find pension schemes.

**Query parameters:**
- `number`: Equals
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

### `POST` /salary/settings/pensionScheme

Create a Pension Scheme.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "pensionSchemeId": 0,
  "number": "<number>",
  "startDate": "<startDate>",
  "endDate": "<endDate>"
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
    "pensionSchemeId": 0,
    "number": "<number>",
    "startDate": "<startDate>",
    "endDate": "<endDate>"
  }
}
```

### `PUT` /salary/settings/pensionScheme/list

Update multiple Pension Schemes.

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

### `POST` /salary/settings/pensionScheme/list

Create multiple Pension Schemes.

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

### `DELETE` /salary/settings/pensionScheme/list

Delete multiple Pension Schemes.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /salary/settings/pensionScheme/{id}

Get Pension Scheme for a specific ID

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
    "pensionSchemeId": 0,
    "number": "<number>",
    "startDate": "<startDate>",
    "endDate": "<endDate>"
  }
}
```

### `PUT` /salary/settings/pensionScheme/{id}

Update a Pension Scheme

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "pensionSchemeId": 0,
  "number": "<number>",
  "startDate": "<startDate>",
  "endDate": "<endDate>"
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
    "pensionSchemeId": 0,
    "number": "<number>",
    "startDate": "<startDate>",
    "endDate": "<endDate>"
  }
}
```

### `DELETE` /salary/settings/pensionScheme/{id}

Delete a Pension Scheme

### `GET` /salary/settings/standardTime

Get all standard times.

**Query parameters:**
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

### `POST` /salary/settings/standardTime

Create standard time.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "company": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "organizationNumber": "<organizationNumber>",
    "email": "<email>",
    "phoneNumber": "<phoneNumber>",
    "phoneNumberMobile": "<phoneNumberMobile>"
  },
  "fromDate": "<fromDate>",
  "hoursPerDa
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
    "fromDate": "<fromDate>",
    "hoursPerDay": 0.0
  }
}
```

### `GET` /salary/settings/standardTime/byDate

Find standard time by date

**Query parameters:**
- `date`: yyyy-MM-dd. Defaults to today.
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
    "fromDate": "<fromDate>",
    "hoursPerDay": 0.0
  }
}
```

### `GET` /salary/settings/standardTime/{id}

Find standard time by ID.

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
    "fromDate": "<fromDate>",
    "hoursPerDay": 0.0
  }
}
```

### `PUT` /salary/settings/standardTime/{id}

Update standard time. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "company": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "organizationNumber": "<organizationNumber>",
    "email": "<email>",
    "phoneNumber": "<phoneNumber>",
    "phoneNumberMobile": "<phoneNumberMobile>"
  },
  "fromDate": "<fromDate>",
  "hoursPerDa
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
    "fromDate": "<fromDate>",
    "hoursPerDay": 0.0
  }
}
```

### `POST` /salary/taxDeduction/reconciliation/context

Create a taxDeduction reconciliation context for a customer

**Request body example:**
```json
{
  "customerId": 0,
  "year": 0,
  "term": 0
}
```

**Response example:**
```json
{
  "value": {
    "year": 0,
    "reconciliationId": 0,
    "term": 0
  }
}
```

### `GET` /salary/taxDeduction/reconciliation/{reconciliationId}/balanceAndOwedAmount

Get tax deduction details for a reconciliation

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "taxDeductionBalance": 0.0,
    "taxDeductionOwedAmount": 0.0,
    "taxDeductionAccountNumber": 0,
    "taxDeductionAccountName": "<taxDeductionAccountName>"
  }
}
```

### `GET` /salary/taxDeduction/reconciliation/{reconciliationId}/overview

Get salary tax deduction data for the reconciliation table

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "registeredPayments": [
      "..."
    ],
    "aggregatedLedgerSum": 0.0,
    "aggregatedAmeldingSum": 0.0,
    "aggregatedTaxAuthoritiesSum": 0.0,
    "aggregatedDiscrepancy": 0.0
  }
}
```

### `GET` /salary/taxDeduction/reconciliation/{reconciliationId}/paymentsOverview

Get salary tax deduction payment overview from start of year to the current reconciliation term

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "payments": [
      "..."
    ],
    "totalLedgerSum": 0.0,
    "totalAmeldingSum": 0.0,
    "totalPaidAmount": 0.0,
    "totalRestAmount": 0.0
  }
}
```

### `POST` /salary/transaction

Create a new salary transaction.

**Query parameters:**
- `generateTaxDeduction`: Generate tax deduction

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
  "year": 0,
  "month": 0,
  "isHistorical": true,
  "paySlipsAvailableDate": "<paySlipsAvailableDate>",
  "payslips": [
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
    "year": 0,
    "month": 0,
    "isHistorical": true,
    "paySlipsAvailableDate": "<paySlipsAvailableDate>",
    "payslips": [
      "..."
    ]
  }
}
```

### `GET` /salary/transaction/{id}

Find salary transaction by ID.

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
    "year": 0,
    "month": 0,
    "isHistorical": true,
    "paySlipsAvailableDate": "<paySlipsAvailableDate>",
    "payslips": [
      "..."
    ]
  }
}
```

### `DELETE` /salary/transaction/{id}

Delete salary transaction by ID.

### `POST` /salary/transaction/{id}/attachment

Upload an attachment to a salary transaction

**Response example:**
```json
{
  "value": 0
}
```

### `POST` /salary/transaction/{id}/attachment/list

Upload multiple attachments to a salary transaction

**Response example:**
```json
{
  "value": 0
}
```

### `PUT` /salary/transaction/{id}/deleteAttachment

Delete attachment.

**Query parameters:**
- `sendToVoucherInbox`: Should the attachment be sent to inbox rather than deleted?
- `split`: If sendToInbox is true, should the attachment be split into one voucher per page?

### `GET` /salary/type

Find salary type corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `number`: Containing
- `name`: Containing
- `description`: Containing
- `showInTimesheet`: Equals
- `isInactive`: Equals
- `employeeIds`: Equals
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

### `GET` /salary/type/{id}

Find salary type by ID.

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
    "number": "<number>",
    "name": "<name>",
    "description": "<description>",
    "showInTimesheet": true,
    "isSickPayable": true,
    "isVacationPayable": true,
    "isTaxable": true,
    "payStatementCodeCode": "<payStatementCodeCode>"
  }
}
```

## Common usage patterns

```bash
# Get payslips
curl -u "0:$TOKEN" "$URL/salary/payslip?fields=id,employee(*)"

# Create salary transaction
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/salary/transaction" -d '{"employee":{"id":123},"salaryType":{"id":1},"amount":50000}'
```
