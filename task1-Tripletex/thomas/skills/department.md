# department

Tripletex API endpoints for managing department resources.

## Endpoints

### `GET` /department

Find department corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
- `departmentNumber`: Containing
- `departmentManagerId`: List of IDs
- `isInactive`: true - return only inactive departments; false - return only active departments; unspecified - retur
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

### `POST` /department

Add new department.

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
  "departmentNumber": "<departmentNumber>",
  "departmentManager": {
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
    "departmentNumber": "<departmentNumber>",
    "displayName": "<displayName>",
    "isInactive": true,
    "businessActivityTypeId": 0
  }
}
```

### `PUT` /department/list

Update multiple departments.

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

### `POST` /department/list

Register new departments.

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

### `GET` /department/query

Wildcard search.

**Query parameters:**
- `id`: List of IDs
- `query`: Containing
- `count`: Number of elements to return
- `fields`: Fields filter pattern
- `isInactive`: true - return only inactive departments; false - return only active departments; unspecified - retur
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

### `GET` /department/{id}

Get department by ID.

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
    "departmentNumber": "<departmentNumber>",
    "displayName": "<displayName>",
    "isInactive": true,
    "businessActivityTypeId": 0
  }
}
```

### `PUT` /department/{id}

Update department.

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
  "departmentNumber": "<departmentNumber>",
  "departmentManager": {
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
    "departmentNumber": "<departmentNumber>",
    "displayName": "<displayName>",
    "isInactive": true,
    "businessActivityTypeId": 0
  }
}
```

### `DELETE` /department/{id}

Delete department by ID

## Common usage patterns

```bash
# List departments
curl -u "0:$TOKEN" "$URL/department?fields=id,name,departmentNumber"

# Create department
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/department" -d '{"name":"Salg","departmentNumber":1}'
```
