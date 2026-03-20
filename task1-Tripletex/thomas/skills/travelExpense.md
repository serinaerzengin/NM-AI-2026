# travelExpense

Tripletex API endpoints for managing travelExpense resources.

## Endpoints

### `GET` /travelExpense

Find travel expenses corresponding with sent data.

**Query parameters:**
- `employeeId`: Equals
- `departmentId`: Equals
- `projectId`: Equals
- `projectManagerId`: Equals
- `departureDateFrom`: From and including
- `returnDateTo`: To and excluding
- `state`: category
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

### `POST` /travelExpense

Create travel expense.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "attestationSteps": [
    "..."
  ],
  "attestation": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "type": "<type>",
    "levels": [
      "..."
    ]
  },
  "project": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "number": "<number>",
    "displayName": "<displayName>",
    "description": "<descriptio
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
    "attestationSteps": [
      "..."
    ]
  }
}
```

### `PUT` /travelExpense/:approve

Approve travel expenses.

**Query parameters:**
- `id`: ID of the elements
- `overrideApprovalFlow`: Override approval flow

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

### `PUT` /travelExpense/:copy

Copy travel expense.

**Query parameters:**
- `id` (required): Element ID

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
    "attestationSteps": [
      "..."
    ]
  }
}
```

### `PUT` /travelExpense/:createVouchers

Create vouchers

**Query parameters:**
- `id`: ID of the elements
- `date` (required): yyyy-MM-dd. Defaults to today.

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

### `PUT` /travelExpense/:deliver

Deliver travel expenses.

**Query parameters:**
- `id`: ID of the elements

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

### `PUT` /travelExpense/:unapprove

Unapprove travel expenses.

**Query parameters:**
- `id`: ID of the elements

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

### `PUT` /travelExpense/:undeliver

Undeliver travel expenses.

**Query parameters:**
- `id`: ID of the elements

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "attestationSteps": [
    "..."
  ],
  "attestation": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "type": "<type>",
    "levels": [
      "..."
    ]
  },
  "project": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "number": "<number>",
    "displayName": "<displayName>",
    "description": "<descriptio
```

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

### `GET` /travelExpense/accommodationAllowance

Find accommodation allowances corresponding with sent data.

**Query parameters:**
- `travelExpenseId`: Equals
- `rateTypeId`: Equals
- `rateCategoryId`: Equals
- `rateFrom`: From and including
- `rateTo`: To and excluding
- `countFrom`: From and including
- `countTo`: To and excluding
- `amountFrom`: From and including
- `amountTo`: To and excluding
- `location`: Containing

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

### `POST` /travelExpense/accommodationAllowance

Create accommodation allowance.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "rateType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  },
  "rateCategory": {
  
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
    "zone": "<zone>",
    "location": "<location>",
    "address": "<address>",
    "count": 0,
    "rate": 0.0
  }
}
```

### `GET` /travelExpense/accommodationAllowance/{id}

Get travel accommodation allowance by ID.

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
    "zone": "<zone>",
    "location": "<location>",
    "address": "<address>",
    "count": 0,
    "rate": 0.0
  }
}
```

### `PUT` /travelExpense/accommodationAllowance/{id}

Update accommodation allowance.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "rateType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  },
  "rateCategory": {
  
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
    "zone": "<zone>",
    "location": "<location>",
    "address": "<address>",
    "count": 0,
    "rate": 0.0
  }
}
```

### `DELETE` /travelExpense/accommodationAllowance/{id}

Delete accommodation allowance.

### `GET` /travelExpense/cost

Find costs corresponding with sent data.

**Query parameters:**
- `travelExpenseId`: Equals
- `vatTypeId`: Equals
- `currencyId`: Equals
- `rateFrom`: From and including
- `rateTo`: To and excluding
- `countFrom`: From and including
- `countTo`: To and excluding
- `amountFrom`: From and including
- `amountTo`: To and excluding
- `location`: Containing

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

### `POST` /travelExpense/cost

Create cost.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "vatType": {
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
  },
  "currency": {
    "
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
    "category": "<category>",
    "comments": "<comments>",
    "rate": 0.0
  }
}
```

### `PUT` /travelExpense/cost/list

Update costs.

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

### `GET` /travelExpense/cost/{id}

Get cost by ID.

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
    "category": "<category>",
    "comments": "<comments>",
    "rate": 0.0
  }
}
```

### `PUT` /travelExpense/cost/{id}

Update cost.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "vatType": {
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
  },
  "currency": {
    "
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
    "category": "<category>",
    "comments": "<comments>",
    "rate": 0.0
  }
}
```

### `DELETE` /travelExpense/cost/{id}

Delete cost.

### `GET` /travelExpense/costCategory

Find cost category corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `description`: Containing
- `isInactive`: Equals
- `showOnEmployeeExpenses`: Equals
- `query`: Equals
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

### `GET` /travelExpense/costCategory/{id}

Get cost category by ID.

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
    "isVatLocked": true,
    "showOnTravelExpenses": true,
    "showOnEmployeeExpenses": true,
    "isInactive": true,
    "sequence": 0
  }
}
```

### `POST` /travelExpense/costParticipant

Create participant on cost.

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
  "employeeId": 0,
  "cost": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "category": "<category>",
    "comments": "<comments>",
    "rate": 0.0
  }
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
    "employeeId": 0
  }
}
```

### `POST` /travelExpense/costParticipant/createCostParticipantAdvanced

Create participant on cost using explicit parameters

**Query parameters:**
- `displayName`: The name of the participant
- `costId` (required): ID of cost
- `employeeId` (required): ID of the employee if it is participant. 0 is allowed if the participant is not an employee

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
    "employeeId": 0
  }
}
```

### `POST` /travelExpense/costParticipant/list

Create participants on cost.

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

### `DELETE` /travelExpense/costParticipant/list

Delete cost participants.

### `GET` /travelExpense/costParticipant/{costId}/costParticipants

Get cost's participants by costId.

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

### `GET` /travelExpense/costParticipant/{id}

Get cost participant by ID.

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
    "employeeId": 0
  }
}
```

### `DELETE` /travelExpense/costParticipant/{id}

Delete cost participant.

### `POST` /travelExpense/drivingStop

Create mileage allowance driving stop.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "locationName": "<locationName>",
  "latitude": 0.0,
  "longitude": 0.0,
  "sortIndex": 0,
  "type": 0,
  "mileageAllowance": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "date": "<date>",
    "departureLocation": "<departureLocation>",
    "destination": "<destination>",
    "km": 0.0,
    "rate": 0.0
  }
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
    "locationName": "<locationName>",
    "latitude": 0.0,
    "longitude": 0.0,
    "sortIndex": 0,
    "type": 0
  }
}
```

### `GET` /travelExpense/drivingStop/{id}

Get driving stop by ID.

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
    "locationName": "<locationName>",
    "latitude": 0.0,
    "longitude": 0.0,
    "sortIndex": 0,
    "type": 0
  }
}
```

### `DELETE` /travelExpense/drivingStop/{id}

Delete mileage allowance stops.

### `GET` /travelExpense/mileageAllowance

Find mileage allowances corresponding with sent data.

**Query parameters:**
- `travelExpenseId`: Equals
- `rateTypeId`: Equals
- `rateCategoryId`: Equals
- `kmFrom`: From and including
- `kmTo`: To and excluding
- `rateFrom`: From and including
- `rateTo`: To and excluding
- `amountFrom`: From and including
- `amountTo`: To and excluding
- `departureLocation`: Containing

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

### `POST` /travelExpense/mileageAllowance

Create mileage allowance.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "rateType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  },
  "rateCategory": {
  
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
    "departureLocation": "<departureLocation>",
    "destination": "<destination>",
    "km": 0.0,
    "rate": 0.0
  }
}
```

### `GET` /travelExpense/mileageAllowance/{id}

Get mileage allowance by ID.

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
    "departureLocation": "<departureLocation>",
    "destination": "<destination>",
    "km": 0.0,
    "rate": 0.0
  }
}
```

### `PUT` /travelExpense/mileageAllowance/{id}

Update mileage allowance.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "rateType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  },
  "rateCategory": {
  
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
    "departureLocation": "<departureLocation>",
    "destination": "<destination>",
    "km": 0.0,
    "rate": 0.0
  }
}
```

### `DELETE` /travelExpense/mileageAllowance/{id}

Delete mileage allowance.

### `GET` /travelExpense/passenger

Find passengers corresponding with sent data.

**Query parameters:**
- `mileageAllowance`: Equals
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

### `POST` /travelExpense/passenger

Create passenger.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "name": "<name>",
  "mileageAllowance": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "date": "<date>",
    "departureLocation": "<departureLocation>",
    "destination": "<destination>",
    "km": 0.0,
    "rate": 0.0
  }
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
    "name": "<name>"
  }
}
```

### `POST` /travelExpense/passenger/list

Create passengers.

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

### `DELETE` /travelExpense/passenger/list

Delete passengers.

### `GET` /travelExpense/passenger/{id}

Get passenger by ID.

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
    "name": "<name>"
  }
}
```

### `PUT` /travelExpense/passenger/{id}

Update passenger.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "name": "<name>",
  "mileageAllowance": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "date": "<date>",
    "departureLocation": "<departureLocation>",
    "destination": "<destination>",
    "km": 0.0,
    "rate": 0.0
  }
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
    "name": "<name>"
  }
}
```

### `DELETE` /travelExpense/passenger/{id}

Delete passenger.

### `GET` /travelExpense/paymentType

Find payment type corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `description`: Containing
- `isInactive`: Equals
- `showOnEmployeeExpenses`: Equals
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

### `GET` /travelExpense/paymentType/{id}

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
    "showOnTravelExpenses": true,
    "showOnEmployeeExpenses": true,
    "isInactive": true,
    "displayName": "<displayName>"
  }
}
```

### `GET` /travelExpense/perDiemCompensation

Find per diem compensations corresponding with sent data.

**Query parameters:**
- `travelExpenseId`: Equals
- `rateTypeId`: Equals
- `rateCategoryId`: Equals
- `overnightAccommodation`: Equals
- `countFrom`: From and including
- `countTo`: To and excluding
- `rateFrom`: From and including
- `rateTo`: To and excluding
- `amountFrom`: From and including
- `amountTo`: To and excluding

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

### `POST` /travelExpense/perDiemCompensation

Create per diem compensation.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "rateType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  },
  "rateCategory": {
  
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
    "countryCode": "<countryCode>",
    "travelExpenseZoneId": 0,
    "overnightAccommodation": "<overnightAccommodation>",
    "location": "<location>",
    "address": "<address>"
  }
}
```

### `GET` /travelExpense/perDiemCompensation/{id}

Get per diem compensation by ID.

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
    "countryCode": "<countryCode>",
    "travelExpenseZoneId": 0,
    "overnightAccommodation": "<overnightAccommodation>",
    "location": "<location>",
    "address": "<address>"
  }
}
```

### `PUT` /travelExpense/perDiemCompensation/{id}

Update per diem compensation.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "travelExpense": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "attestationSteps": [
      "..."
    ]
  },
  "rateType": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  },
  "rateCategory": {
  
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
    "countryCode": "<countryCode>",
    "travelExpenseZoneId": 0,
    "overnightAccommodation": "<overnightAccommodation>",
    "location": "<location>",
    "address": "<address>"
  }
}
```

### `DELETE` /travelExpense/perDiemCompensation/{id}

Delete per diem compensation.

### `GET` /travelExpense/rate

Find rates corresponding with sent data.

**Query parameters:**
- `rateCategoryId`: Equals
- `type`: Equals
- `isValidDayTrip`: Equals
- `isValidAccommodation`: Equals
- `isValidDomestic`: Equals
- `isValidForeignTravel`: Equals
- `requiresZone`: Equals
- `requiresOvernightAccommodation`: Equals
- `dateFrom`: From and including
- `dateTo`: To and excluding

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

### `GET` /travelExpense/rate/{id}

Get travel expense rate by ID.

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
    "zone": "<zone>",
    "rate": 0.0,
    "breakfastDeductionRate": 0.0,
    "lunchDeductionRate": 0.0,
    "dinnerDeductionRate": 0.0
  }
}
```

### `GET` /travelExpense/rateCategory

Find rate categories corresponding with sent data.

**Query parameters:**
- `type`: Equals
- `name`: Containing
- `travelReportRateCategoryGroupId`: Equals
- `ameldingWageCode`: Containing
- `wageCodeNumber`: Equals
- `isValidDayTrip`: Equals
- `isValidAccommodation`: Equals
- `isValidDomestic`: Equals
- `requiresZone`: Equals
- `isRequiresOvernightAccommodation`: Equals

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

### `GET` /travelExpense/rateCategory/{id}

Get travel expense rate category by ID.

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
    "ameldingWageCode": 0,
    "wageCodeNumber": "<wageCodeNumber>",
    "isValidDayTrip": true,
    "isValidAccommodation": true,
    "isValidDomestic": true,
    "isValidForeignTravel": true,
    "isRequiresZone": true
  }
}
```

### `GET` /travelExpense/rateCategoryGroup

Find rate categoriy groups corresponding with sent data.

**Query parameters:**
- `name`: Containing
- `isForeignTravel`: Equals
- `dateFrom`: From and including
- `dateTo`: To and excluding
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

### `GET` /travelExpense/rateCategoryGroup/{id}

Get travel report rate category group by ID.

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
    "isForeignTravel": true,
    "fromDate": "<fromDate>",
    "toDate": "<toDate>"
  }
}
```

### `GET` /travelExpense/settings

Get travel expense settings of logged in company.

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
    "useRates": true,
    "approvalRequired": true,
    "taxFreePerDiemRates": true,
    "taxFreeMileageRates": 0,
    "perDiemNotCompensated": true,
    "accommodationNotCompensated": true,
    "mileageNotCompensated": true,
    "canApproveOwnExpenses": true
  }
}
```

### `GET` /travelExpense/zone

Find travel expense zones corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `code`: List of IDs
- `isDisabled`: Equals
- `query`: Containing
- `date`: yyyy-MM-dd. Defaults to today.
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

### `GET` /travelExpense/zone/{id}

Get travel expense zone by ID.

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
    "countryCode": "<countryCode>",
    "zoneName": "<zoneName>",
    "isDisabled": true,
    "governmentName": "<governmentName>",
    "continent": "<continent>",
    "fromDate": "<fromDate>",
    "toDate": "<toDate>",
    "currencyId": 0
  }
}
```

### `GET` /travelExpense/{id}

Get travel expense by ID.

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
    "attestationSteps": [
      "..."
    ]
  }
}
```

### `PUT` /travelExpense/{id}

Update travel expense.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "attestationSteps": [
    "..."
  ],
  "attestation": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "type": "<type>",
    "levels": [
      "..."
    ]
  },
  "project": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "number": "<number>",
    "displayName": "<displayName>",
    "description": "<descriptio
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
    "attestationSteps": [
      "..."
    ]
  }
}
```

### `DELETE` /travelExpense/{id}

Delete travel expense.

### `PUT` /travelExpense/{id}/convert

Convert travel to/from employee expense.

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
    "attestationSteps": [
      "..."
    ]
  }
}
```

### `GET` /travelExpense/{travelExpenseId}/attachment

Get attachment by travel expense ID.

### `POST` /travelExpense/{travelExpenseId}/attachment

Upload attachment to travel expense.

**Query parameters:**
- `createNewCost`: Create new cost row when you add the attachment

### `DELETE` /travelExpense/{travelExpenseId}/attachment

Delete attachment.

**Query parameters:**
- `version`: Version of voucher containing the attachment to delete.
- `sendToInbox`: Should the attachment be sent to inbox rather than deleted?
- `split`: If sendToInbox is true, should the attachment be split into one voucher per page?

### `POST` /travelExpense/{travelExpenseId}/attachment/list

Upload multiple attachments to travel expense.

**Query parameters:**
- `createNewCost`: Create new cost row when you add the attachment

## Common usage patterns

```bash
# List travel expenses
curl -u "0:$TOKEN" "$URL/travelExpense?fields=id,title,employee(*)"

# Create travel expense
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/travelExpense" -d '{"employee":{"id":123},"title":"Reise Oslo","departureDate":"2026-03-19","returnDate":"2026-03-20"}'

# Delete travel expense
curl -X DELETE -u "0:$TOKEN" "$URL/travelExpense/789"
```
