# project

Tripletex API endpoints for managing project resources.

## Endpoints

### `GET` /project

Find projects corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
- `number`: Equals
- `isOffer`: Equals
- `projectManagerId`: List of IDs
- `customerAccountManagerId`: List of IDs
- `employeeInProjectId`: List of IDs
- `departmentId`: List of IDs
- `startDateFrom`: From and including
- `startDateTo`: To and excluding

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

### `POST` /project

Add new project.

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
  "number": "<number>",
  "displayName": "<displayName>",
  "description": "<description>",
  "projectManager": {
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
    "number": "<number>",
    "displayName": "<displayName>",
    "description": "<description>",
    "startDate": "<startDate>"
  }
}
```

### `DELETE` /project

[BETA] Delete multiple projects.

### `GET` /project/>forTimeSheet

Find projects applicable for time sheet registration on a specific day.

**Query parameters:**
- `includeProjectOffers`: Equals
- `employeeId`: Employee ID. Defaults to ID of token owner.
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

### `GET` /project/batchPeriod/budgetStatusByProjectIds

Get the budget status for the projects in the specific period.

**Query parameters:**
- `ids` (required): ID of the elements
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

### `GET` /project/batchPeriod/invoicingReserveByProjectIds

Get the invoicing reserve for the projects in the specific period.

**Query parameters:**
- `ids` (required): ID of the elements
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

### `GET` /project/category

Find project categories corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
- `number`: Equals
- `description`: Containing
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

### `POST` /project/category

Add new project category.

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
  "number": "<number>",
  "description": "<description>",
  "displayName": "<displayName>"
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
    "name": "<name>",
    "number": "<number>",
    "description": "<description>",
    "displayName": "<displayName>"
  }
}
```

### `GET` /project/category/{id}

Find project category by ID.

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
    "description": "<description>",
    "displayName": "<displayName>"
  }
}
```

### `PUT` /project/category/{id}

Update project category.

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
  "number": "<number>",
  "description": "<description>",
  "displayName": "<displayName>"
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
    "name": "<name>",
    "number": "<number>",
    "description": "<description>",
    "displayName": "<displayName>"
  }
}
```

### `GET` /project/controlForm

[BETA] Get project control forms by project ID.

**Query parameters:**
- `projectId` (required): Project ID
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

### `GET` /project/controlForm/{id}

[BETA] Get project control form by ID.

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
    "completed": true,
    "signatureRequired": true,
    "signed": true,
    "controlForm": "<controlForm>"
  }
}
```

### `GET` /project/controlFormType

[BETA] Get project control form types

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

### `GET` /project/controlFormType/{id}

[BETA] Get project control form type by ID.

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

### `PUT` /project/dynamicControlForm/{id}/:copyFieldValuesFromLastEditedForm

Into each section in the specified form that only has empty or default values, and copyFieldValuesByDefault set as true in the form's template, copy field values from the equivalent section in the most recently edited control form. Signed or completed forms will not be affected.

### `GET` /project/hourlyRates

Find project hourly rates corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `projectId`: List of IDs
- `type`: Equals
- `startDateFrom`: From and including
- `startDateTo`: To and excluding
- `showInProjectOrder`: Equals
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

### `POST` /project/hourlyRates

Create a project hourly rate. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
    "description": "<description>",
    "startDate": "<startDate>"
  },
  "startDate": "<startDate>",
  "showInProjectOrder": true,
  "hourlyRateModel": "<hourlyRateModel>",
  "projectSpecificRates": [
    "..."
  ],
  "fixedRate": 0.0
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
    "startDate": "<startDate>",
    "showInProjectOrder": true,
    "hourlyRateModel": "<hourlyRateModel>",
    "projectSpecificRates": [
      "..."
    ],
    "fixedRate": 0.0
  }
}
```

### `DELETE` /project/hourlyRates/deleteByProjectIds

Delete project hourly rates by project id.

**Query parameters:**
- `ids` (required): ID of the elements
- `date` (required): yyyy-MM-dd. Defaults to today.

### `PUT` /project/hourlyRates/list

Update multiple project hourly rates.

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

### `POST` /project/hourlyRates/list

Create multiple project hourly rates.

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

### `DELETE` /project/hourlyRates/list

Delete project hourly rates.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /project/hourlyRates/projectSpecificRates

Find project specific rates corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `projectHourlyRateId`: List of IDs
- `employeeId`: List of IDs
- `activityId`: List of IDs
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

### `POST` /project/hourlyRates/projectSpecificRates

Create new project specific rate. 

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "hourlyRate": 0.0,
  "hourlyCostPercentage": 0.0,
  "projectHourlyRate": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "startDate": "<startDate>",
    "showInProjectOrder": true,
    "hourlyRateModel": "<hourlyRateModel>",
    "projectSpecificRates": [
      "..."
    ],
    "fixedRate": 0.0
  },
  "employee": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."

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
    "hourlyRate": 0.0,
    "hourlyCostPercentage": 0.0
  }
}
```

### `PUT` /project/hourlyRates/projectSpecificRates/list

Update multiple project specific rates.

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

### `POST` /project/hourlyRates/projectSpecificRates/list

Create multiple new project specific rates.

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

### `DELETE` /project/hourlyRates/projectSpecificRates/list

Delete project specific rates.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /project/hourlyRates/projectSpecificRates/{id}

Find project specific rate by ID.

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
    "hourlyRate": 0.0,
    "hourlyCostPercentage": 0.0
  }
}
```

### `PUT` /project/hourlyRates/projectSpecificRates/{id}

Update a project specific rate.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "hourlyRate": 0.0,
  "hourlyCostPercentage": 0.0,
  "projectHourlyRate": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "startDate": "<startDate>",
    "showInProjectOrder": true,
    "hourlyRateModel": "<hourlyRateModel>",
    "projectSpecificRates": [
      "..."
    ],
    "fixedRate": 0.0
  },
  "employee": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."

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
    "hourlyRate": 0.0,
    "hourlyCostPercentage": 0.0
  }
}
```

### `DELETE` /project/hourlyRates/projectSpecificRates/{id}

Delete project specific rate 

### `PUT` /project/hourlyRates/updateOrAddHourRates

Update or add the same project hourly rate from project overview.

**Query parameters:**
- `ids` (required): ID of the elements

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "startDate": "<startDate>",
  "hourlyRateModel": "<hourlyRateModel>",
  "projectSpecificRates": [
    "..."
  ],
  "fixedRate": 0.0
}
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

### `GET` /project/hourlyRates/{id}

Find project hourly rate by ID.

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
    "startDate": "<startDate>",
    "showInProjectOrder": true,
    "hourlyRateModel": "<hourlyRateModel>",
    "projectSpecificRates": [
      "..."
    ],
    "fixedRate": 0.0
  }
}
```

### `PUT` /project/hourlyRates/{id}

Update a project hourly rate.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
    "description": "<description>",
    "startDate": "<startDate>"
  },
  "startDate": "<startDate>",
  "showInProjectOrder": true,
  "hourlyRateModel": "<hourlyRateModel>",
  "projectSpecificRates": [
    "..."
  ],
  "fixedRate": 0.0
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
    "startDate": "<startDate>",
    "showInProjectOrder": true,
    "hourlyRateModel": "<hourlyRateModel>",
    "projectSpecificRates": [
      "..."
    ],
    "fixedRate": 0.0
  }
}
```

### `DELETE` /project/hourlyRates/{id}

Delete Project Hourly Rate 

### `POST` /project/import

Upload project import file.

**Query parameters:**
- `fileFormat` (required): File format
- `encoding`: Encoding
- `delimiter`: Delimiter
- `ignoreFirstRow`: Ignore first row

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

### `PUT` /project/list

[BETA] Update multiple projects.

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

### `POST` /project/list

[BETA] Register new projects. Multiple projects for different users can be sent in the same request.

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

### `DELETE` /project/list

[BETA] Delete projects.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /project/number/{number}

Find project by number.

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
    "description": "<description>",
    "startDate": "<startDate>"
  }
}
```

### `GET` /project/orderline

[BETA] Find all order lines for project.

**Query parameters:**
- `projectId` (required): Equals
- `isBudget`: Equals
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

### `POST` /project/orderline

[BETA] Create order line. When creating several order lines, use /list for better performance.

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

### `POST` /project/orderline/list

[BETA] Create multiple order lines.

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

### `GET` /project/orderline/orderLineTemplate

[BETA] Get order line template from project and product

**Query parameters:**
- `projectId` (required): Equals
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

### `GET` /project/orderline/query

[BETA] Wildcard search.

**Query parameters:**
- `id`: List of IDs
- `projectId`: Equals
- `query`: Containing
- `isBudget`: Equals
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

### `GET` /project/orderline/{id}

[BETA] Get order line by ID.

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

### `PUT` /project/orderline/{id}

[BETA] Update project orderline.

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

### `DELETE` /project/orderline/{id}

Delete order line by ID.

### `POST` /project/participant

[BETA] Add new project participant.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
    "description": "<description>",
    "startDate": "<startDate>"
  },
  "employee": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "firstName": "<firstName>",
    "lastName": "<lastName>",

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
    "adminAccess": true
  }
}
```

### `POST` /project/participant/list

[BETA] Add new project participant. Multiple project participants can be sent in the same request.

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

### `DELETE` /project/participant/list

[BETA] Delete project participants.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /project/participant/{id}

[BETA] Find project participant by ID.

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
    "adminAccess": true
  }
}
```

### `PUT` /project/participant/{id}

[BETA] Update project participant.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
    "description": "<description>",
    "startDate": "<startDate>"
  },
  "employee": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "firstName": "<firstName>",
    "lastName": "<lastName>",

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
    "adminAccess": true
  }
}
```

### `POST` /project/projectActivity

Add project activity.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "activity": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "number": "<number>",
    "description": "<description>",
    "activityType": "<activityType>",
    "isProjectActivity": true,
    "isGeneral": true,
    "isTask": true,
    "isDisabled": true
  },
  "project": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<u
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
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "isClosed": true,
    "budgetHours": 0.0,
    "budgetHourlyRateCurrency": 0.0,
    "budgetFeeCurrency": 0.0
  }
}
```

### `DELETE` /project/projectActivity/list

Delete project activities

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /project/projectActivity/{id}

Find project activity by id

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
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "isClosed": true,
    "budgetHours": 0.0,
    "budgetHourlyRateCurrency": 0.0,
    "budgetFeeCurrency": 0.0
  }
}
```

### `DELETE` /project/projectActivity/{id}

Delete project activity

### `GET` /project/resourcePlanBudget

Get resource plan entries in the specified period.

**Query parameters:**
- `projectId`: Equals
- `periodStart` (required): From and including
- `periodEnd` (required): To and excluding
- `periodType` (required): Equals
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "projectId": 0,
    "projectName": "<projectName>",
    "periodStart": "<periodStart>",
    "periodEnd": "<periodEnd>",
    "periodType": "<periodType>",
    "activityEntries": [
      "..."
    ]
  }
}
```

### `GET` /project/settings

Get project settings of logged in company.

**Query parameters:**
- `useNkode`: Equals
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "approveHourLists": true,
    "approveInvoices": true,
    "markReadyForInvoicing": true,
    "historicalInformation": true,
    "projectForecast": true,
    "budgetOnSubcontracts": true,
    "projectCategories": true,
    "referenceFee": true,
    "sortOrderProjects": "<sortOrderProjects>",
    "autoCloseInvoicedProjects": true,
    "mustApproveRegisteredHours": true,
    "showProjectOrderLinesToAllProjectParticipants": true
  }
}
```

### `PUT` /project/settings

Update project settings for company

**Request body example:**
```json
{
  "approveHourLists": true,
  "approveInvoices": true,
  "markReadyForInvoicing": true,
  "historicalInformation": true,
  "projectForecast": true,
  "budgetOnSubcontracts": true,
  "projectCategories": true,
  "referenceFee": true,
  "sortOrderProjects": "<sortOrderProjects>",
  "autoCloseInvoicedProjects": true,
  "mustApproveRegisteredHours": true,
  "showProjectOrderLinesToAllProjectParticipants": true
}
```

**Response example:**
```json
{
  "value": {
    "approveHourLists": true,
    "approveInvoices": true,
    "markReadyForInvoicing": true,
    "historicalInformation": true,
    "projectForecast": true,
    "budgetOnSubcontracts": true,
    "projectCategories": true,
    "referenceFee": true,
    "sortOrderProjects": "<sortOrderProjects>",
    "autoCloseInvoicedProjects": true,
    "mustApproveRegisteredHours": true,
    "showProjectOrderLinesToAllProjectParticipants": true
  }
}
```

### `GET` /project/subcontract

Find project sub-contracts corresponding with sent data.

**Query parameters:**
- `projectId` (required): Equals
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

### `POST` /project/subcontract

Add new project sub-contract.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
    "description": "<description>",
    "startDate": "<startDate>"
  },
  "company": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
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
    "budgetFeeCurrency": 0.0,
    "budgetExpensesCurrency": 0.0,
    "budgetIncomeCurrency": 0.0,
    "budgetNetAmountCurrency": 0.0,
    "displayName": "<displayName>",
    "name": "<name>"
  }
}
```

### `GET` /project/subcontract/query

Wildcard search.

**Query parameters:**
- `id`: List of IDs
- `projectId`: Equals
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

### `GET` /project/subcontract/{id}

Find project sub-contract by ID.

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
    "budgetFeeCurrency": 0.0,
    "budgetExpensesCurrency": 0.0,
    "budgetIncomeCurrency": 0.0,
    "budgetNetAmountCurrency": 0.0,
    "displayName": "<displayName>",
    "name": "<name>"
  }
}
```

### `PUT` /project/subcontract/{id}

Update project sub-contract.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
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
    "description": "<description>",
    "startDate": "<startDate>"
  },
  "company": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
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
    "budgetFeeCurrency": 0.0,
    "budgetExpensesCurrency": 0.0,
    "budgetIncomeCurrency": 0.0,
    "budgetNetAmountCurrency": 0.0,
    "displayName": "<displayName>",
    "name": "<name>"
  }
}
```

### `DELETE` /project/subcontract/{id}

Delete project sub-contract by ID.

### `GET` /project/task

Find all tasks for project.

**Query parameters:**
- `projectId` (required): Equals
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

### `GET` /project/template/{id}

Get project template by ID.

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "name": "<name>",
    "startDate": "<startDate>",
    "endDate": "<endDate>",
    "isInternal": true,
    "number": "<number>",
    "displayNameFormat": "<displayNameFormat>",
    "reference": "<reference>",
    "externalAccountsNumber": "<externalAccountsNumber>"
  }
}
```

### `GET` /project/{id}

Find project by ID.

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
    "description": "<description>",
    "startDate": "<startDate>"
  }
}
```

### `PUT` /project/{id}

[BETA] Update project.

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
  "number": "<number>",
  "displayName": "<displayName>",
  "description": "<description>",
  "projectManager": {
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
    "number": "<number>",
    "displayName": "<displayName>",
    "description": "<description>",
    "startDate": "<startDate>"
  }
}
```

### `DELETE` /project/{id}

[BETA] Delete project.

### `GET` /project/{id}/period/budgetStatus

Get the budget status for the project period

**Query parameters:**
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "totalTotalIncomeCurrency": 0.0,
    "budgetTotalIncomeCurrency": 0.0,
    "budgetTotalCostCurrency": 0.0
  }
}
```

### `GET` /project/{id}/period/hourlistReport

Find hourlist report by project period.

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "chargeableHours": 0.0,
    "nonChargeableHours": 0.0,
    "approvedButUnchargedHours": 0.0,
    "nonApprovedHours": 0.0,
    "registeredHours": 0.0
  }
}
```

### `GET` /project/{id}/period/invoiced

Find invoiced info by project period.

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "sumAmountPaid": 0.0,
    "sumAmountOutstanding": 0.0,
    "sumAmountDue": 0.0,
    "sumAmountDueOutstanding": 0.0,
    "sumAmount": 0.0
  }
}
```

### `GET` /project/{id}/period/invoicingReserve

Find invoicing reserve by project period.

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "invoiceFeeReserveCurrency": 0.0,
    "periodOrderLinesIncomeCurrency": 0.0,
    "invoiceExtracostsReserveCurrency": 0.0,
    "invoiceAkontoReserveAmountCurrency": 0.0,
    "invoiceReserveTotalAmountCurrency": 0.0
  }
}
```

### `GET` /project/{id}/period/monthlyStatus

Find overall status by project period.

**Query parameters:**
- `dateFrom` (required): Will be set to the first day of the provided date's month. Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Must be in the same year as dateFrom. Will be set to the last day of the provided date's month. Form
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

### `GET` /project/{id}/period/overallStatus

Find overall status by project period.

**Query parameters:**
- `dateFrom` (required): Format is yyyy-MM-dd (from and incl.).
- `dateTo` (required): Format is yyyy-MM-dd (to and excl.).
- `fields`: Fields filter pattern

**Response example:**
```json
{
  "value": {
    "income": 0.0,
    "costs": 0.0
  }
}
```

## Common usage patterns

```bash
# Create project
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/project" -d '{"name":"Prosjekt X","number":"P001","projectManager":{"id":123},"customer":{"id":456}}'
```
