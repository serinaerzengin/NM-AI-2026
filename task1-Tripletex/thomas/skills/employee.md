# employee

Tripletex API endpoints for managing employee resources.

## IMPORTANT: Making an employee an administrator (kontoadministrator)

To make an employee an account administrator, you MUST:
1. Create the employee with `"userType": "EXTENDED"` (NOT "STANDARD")
2. After creation, call `grant_employee_entitlements` with `template="ALL_PRIVILEGES"` and the employee's ID

Example flow:
```
1. create_employee(body='{"firstName":"Ola","lastName":"Nordmann","email":"ola@test.no","userType":"EXTENDED"}')
   → get the employee ID from response
2. grant_employee_entitlements(employee_id=12345, template="ALL_PRIVILEGES")
```

Available entitlement templates:
- ALL_PRIVILEGES — full admin (kontoadministrator)
- INVOICING_MANAGER — invoicing access
- PERSONELL_MANAGER — personnel management
- ACCOUNTANT — accounting access
- DEPARTMENT_LEADER — department leader
- NONE_PRIVILEGES — remove all

## Endpoints

### `GET` /employee

Find employees corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `firstName`: Containing
- `lastName`: Containing
- `employeeNumber`: Equals
- `email`: Containing
- `allowInformationRegistration`: Equals
- `includeContacts`: Equals
- `departmentId`: List of IDs
- `onlyProjectManagers`: Equals
- `onlyContacts`: Equals

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

### `POST` /employee

Create one employee.

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

### `GET` /employee/category

Find employee category corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
- `number`: List of IDs
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

### `POST` /employee/category

Create a new employee category.

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
  "name": "<name>",
  "number": "<number>",
  "description": "<description>"
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
    "name": "<name>",
    "number": "<number>",
    "description": "<description>"
  }
}
```

### `PUT` /employee/category/list

Update multiple employee categories.

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

### `POST` /employee/category/list

Create new employee categories.

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

### `DELETE` /employee/category/list

Delete multiple employee categories

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /employee/category/{id}

Get employee category by ID.

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
    "name": "<name>",
    "number": "<number>",
    "description": "<description>"
  }
}
```

### `PUT` /employee/category/{id}

Update employee category information.

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
  "name": "<name>",
  "number": "<number>",
  "description": "<description>"
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
    "name": "<name>",
    "number": "<number>",
    "description": "<description>"
  }
}
```

### `DELETE` /employee/category/{id}

Delete employee category by ID

### `GET` /employee/employment

Find all employments for employee.

**Query parameters:**
- `employeeId`: Element ID
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

### `POST` /employee/employment

Create employment.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employee": {
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
  },
  "employmentId": "<employmentId>",
  "startDate": "<startDate>",
  
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
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  }
}
```

### `GET` /employee/employment/details

Find all employmentdetails for employment.

**Query parameters:**
- `employmentId`: List of IDs
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

### `POST` /employee/employment/details

Create employment details.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employment": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  },
  "date": "<date>",
  "employmentType": "<employmentType>",
  "employmen
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
    "employmentType": "<employmentType>",
    "employmentForm": "<employmentForm>",
    "remunerationType": "<remunerationType>",
    "workingHoursScheme": "<workingHoursScheme>",
    "shiftDurationHours": 0.0
  }
}
```

### `GET` /employee/employment/details/{id}

Find employment details by ID.

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
    "employmentType": "<employmentType>",
    "employmentForm": "<employmentForm>",
    "remunerationType": "<remunerationType>",
    "workingHoursScheme": "<workingHoursScheme>",
    "shiftDurationHours": 0.0
  }
}
```

### `PUT` /employee/employment/details/{id}

Update employment details. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employment": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  },
  "date": "<date>",
  "employmentType": "<employmentType>",
  "employmen
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
    "employmentType": "<employmentType>",
    "employmentForm": "<employmentForm>",
    "remunerationType": "<remunerationType>",
    "workingHoursScheme": "<workingHoursScheme>",
    "shiftDurationHours": 0.0
  }
}
```

### `GET` /employee/employment/employmentType

Find all employment type IDs.

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

### `GET` /employee/employment/employmentType/employmentEndReasonType

Find all employment end reason type IDs.

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

### `GET` /employee/employment/employmentType/employmentFormType

Find all employment form type IDs.

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

### `GET` /employee/employment/employmentType/maritimeEmploymentType

Find all maritime employment type IDs.

**Query parameters:**
- `type` (required): maritimeEmploymentType
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

### `GET` /employee/employment/employmentType/salaryType

Find all salary type IDs.

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

### `GET` /employee/employment/employmentType/scheduleType

Find all schedule type IDs.

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

### `GET` /employee/employment/leaveOfAbsence

Find all leave of absence corresponding with the sent data.

**Query parameters:**
- `employmentIds`: List of IDs
- `date`: yyyy-MM-dd. Defaults to today.
- `minPercentage`: Must be between 0-100.
- `maxPercentage`: Must be between 0-100.
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

### `POST` /employee/employment/leaveOfAbsence

Create leave of absence.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employment": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  },
  "importedLeaveOfAbsenceId": "<importedLeaveOfAbsenceId>",
  "startDate
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
    "importedLeaveOfAbsenceId": "<importedLeaveOfAbsenceId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "percentage": 0.0,
    "isWageDeduction": true,
    "type": "<type>"
  }
}
```

### `POST` /employee/employment/leaveOfAbsence/list

Create multiple leave of absences.

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

### `GET` /employee/employment/leaveOfAbsence/{id}

Find leave of absence by ID.

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
    "importedLeaveOfAbsenceId": "<importedLeaveOfAbsenceId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "percentage": 0.0,
    "isWageDeduction": true,
    "type": "<type>"
  }
}
```

### `PUT` /employee/employment/leaveOfAbsence/{id}

Update leave of absence.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employment": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  },
  "importedLeaveOfAbsenceId": "<importedLeaveOfAbsenceId>",
  "startDate
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
    "importedLeaveOfAbsenceId": "<importedLeaveOfAbsenceId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "percentage": 0.0,
    "isWageDeduction": true,
    "type": "<type>"
  }
}
```

### `GET` /employee/employment/leaveOfAbsenceType

Find all leave of absence type IDs.

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

### `GET` /employee/employment/occupationCode

Find all profession codes.

**Query parameters:**
- `id`: Element ID
- `nameNO`: Containing
- `code`: Containing
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

### `GET` /employee/employment/occupationCode/{id}

Get occupation by ID.

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
    "nameNO": "<nameNO>",
    "code": "<code>"
  }
}
```

### `GET` /employee/employment/remunerationType

Find all remuneration type IDs.

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

### `GET` /employee/employment/workingHoursScheme

Find working hours scheme ID.

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

### `GET` /employee/employment/{id}

Find employment by ID.

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
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  }
}
```

### `PUT` /employee/employment/{id}

Update employemnt. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employee": {
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
  },
  "employmentId": "<employmentId>",
  "startDate": "<startDate>",
  
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
    "employmentId": "<employmentId>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "employmentEndReason": "<employmentEndReason>",
    "lastSalaryChangeDate": "<lastSalaryChangeDate>",
    "noEmploymentRelationship": true
  }
}
```

### `GET` /employee/entitlement

Find all entitlements for user.

**Query parameters:**
- `employeeId`: Employee ID. Defaults to ID of token owner.
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

### `PUT` /employee/entitlement/:grantClientEntitlementsByTemplate

[BETA] Update employee entitlements in client account.

**Query parameters:**
- `employeeId` (required): Employee ID
- `customerId` (required): Client ID
- `template` (required): Template
- `addToExisting`: Add template to existing entitlements

### `PUT` /employee/entitlement/:grantEntitlementsByTemplate

[BETA] Update employee entitlements.

**Query parameters:**
- `employeeId` (required): Employee ID
- `template` (required): Template

### `GET` /employee/entitlement/client

[BETA] Find all entitlements at client for user.

**Query parameters:**
- `employeeId`: Employee ID. Defaults to ID of token owner.
- `customerId`: Client ID
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

### `GET` /employee/entitlement/{id}

Get entitlement by ID.

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
    "entitlementId": 0
  }
}
```

### `GET` /employee/hourlyCostAndRate

Find all hourly cost and rates for employee.

**Query parameters:**
- `employeeId`: Employee ID. Defaults to ID of token owner.
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

### `POST` /employee/hourlyCostAndRate

Create hourly cost and rate.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employee": {
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
  },
  "date": "<date>",
  "rate": 0.0,
  "budgetRate": 0.0,
  "hourCostR
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
    "rate": 0.0,
    "budgetRate": 0.0,
    "hourCostRate": 0.0
  }
}
```

### `GET` /employee/hourlyCostAndRate/{id}

Find hourly cost and rate by ID.

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
    "rate": 0.0,
    "budgetRate": 0.0,
    "hourCostRate": 0.0
  }
}
```

### `PUT` /employee/hourlyCostAndRate/{id}

Update hourly cost and rate. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employee": {
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
  },
  "date": "<date>",
  "rate": 0.0,
  "budgetRate": 0.0,
  "hourCostR
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
    "rate": 0.0,
    "budgetRate": 0.0,
    "hourCostRate": 0.0
  }
}
```

### `POST` /employee/list

Create several employees.

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

### `GET` /employee/nextOfKin

Find all next of kin for employee.

**Query parameters:**
- `employeeId`: Employee ID. Defaults to ID of token owner.
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

### `POST` /employee/nextOfKin

Create next of kin.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employee": {
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
  },
  "name": "<name>",
  "phoneNumber": "<phoneNumber>",
  "address": "
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
    "name": "<name>",
    "phoneNumber": "<phoneNumber>",
    "address": "<address>",
    "typeOfRelationship": "<typeOfRelationship>"
  }
}
```

### `GET` /employee/nextOfKin/{id}

Find next of kin by ID.

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
    "phoneNumber": "<phoneNumber>",
    "address": "<address>",
    "typeOfRelationship": "<typeOfRelationship>"
  }
}
```

### `PUT` /employee/nextOfKin/{id}

Update next of kin. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employee": {
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
  },
  "name": "<name>",
  "phoneNumber": "<phoneNumber>",
  "address": "
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
    "name": "<name>",
    "phoneNumber": "<phoneNumber>",
    "address": "<address>",
    "typeOfRelationship": "<typeOfRelationship>"
  }
}
```

### `GET` /employee/preferences

Find employee preferences corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `employeeId`: Equals
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
    "employeeId": 0,
    "companyId": 0,
    "filterOnProjectParticipant": true,
    "filterOnProjectManager": true,
    "language": "<language>"
  }
}
```

### `PUT` /employee/preferences/:changeLanguage

Change current employees language to the given language

**Query parameters:**
- `language`: Language to change to

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
    "employeeId": 0,
    "companyId": 0,
    "filterOnProjectParticipant": true,
    "filterOnProjectManager": true,
    "language": "<language>"
  }
}
```

### `GET` /employee/preferences/>loggedInEmployeePreferences

Get employee preferences for current user

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
    "employeeId": 0,
    "companyId": 0,
    "filterOnProjectParticipant": true,
    "filterOnProjectManager": true,
    "language": "<language>"
  }
}
```

### `PUT` /employee/preferences/list

Update multiple employee preferences.

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

### `PUT` /employee/preferences/{id}

Update employee preferences information.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "employeeId": 0,
  "companyId": 0,
  "filterOnProjectParticipant": true,
  "filterOnProjectManager": true,
  "language": "<language>"
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
    "employeeId": 0,
    "companyId": 0,
    "filterOnProjectParticipant": true,
    "filterOnProjectManager": true,
    "language": "<language>"
  }
}
```

### `GET` /employee/searchForEmployeesAndContacts

Get employees and contacts by parameters. Include contacts by default.

**Query parameters:**
- `id`: List of IDs
- `firstName`: Containing
- `lastName`: Containing
- `email`: Containing
- `includeContacts`: Equals
- `isInactive`: Equals
- `hasSystemAccess`: Equals
- `excludeReadOnly`: Equals
- `fields`: Fields filter pattern
- `from`: From index

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

### `GET` /employee/standardTime

Find all standard times for employee.

**Query parameters:**
- `employeeId`: Employee ID. Defaults to ID of token owner.
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

### `POST` /employee/standardTime

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
  "employee": {
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
  },
  "fromDate": "<fromDate>",
  "hoursPerDay": 0.0
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
    "fromDate": "<fromDate>",
    "hoursPerDay": 0.0
  }
}
```

### `GET` /employee/standardTime/byDate

Find standard time for employee by date.

**Query parameters:**
- `employeeId`: Employee ID. Defaults to ID of token owner.
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

### `GET` /employee/standardTime/{id}

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

### `PUT` /employee/standardTime/{id}

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
  "employee": {
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
  },
  "fromDate": "<fromDate>",
  "hoursPerDay": 0.0
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
    "fromDate": "<fromDate>",
    "hoursPerDay": 0.0
  }
}
```

### `GET` /employee/{id}

Get employee by ID.

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

### `PUT` /employee/{id}

Update employee.

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

## Common usage patterns

```bash
# List employees
curl -u "0:$TOKEN" "$URL/employee?fields=id,firstName,lastName,email"

# Create employee
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/employee" -d '{"firstName":"Ola","lastName":"Nordmann","email":"ola@test.no"}'

# Get employee by ID
curl -u "0:$TOKEN" "$URL/employee/123?fields=*"

# Update employee
curl -X PUT -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/employee/123" -d '{"id":123,"firstName":"Ola","lastName":"Nordmann","email":"new@test.no"}'
```
