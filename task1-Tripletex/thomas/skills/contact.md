# contact

Tripletex API endpoints for managing contact resources.

## Endpoints

### `GET` /contact

Find contacts corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `firstName`: Containing
- `lastName`: Containing
- `email`: Containing
- `customerId`: List of IDs
- `departmentId`: List of IDs
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

### `POST` /contact

Create contact.

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
    "isoAlpha3Code": "<isoAlpha3Code>",
    "isoNumericCode": "<isoNumericCode>"
  },
  "pho
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
    "email": "<email>",
    "phoneNumberMobile": "<phoneNumberMobile>",
    "phoneNumberWork": "<phoneNumberWork>"
  }
}
```

### `POST` /contact/list

Create multiple contacts.

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

### `DELETE` /contact/list

[BETA] Delete multiple contacts.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /contact/{id}

Get contact by ID.

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
    "email": "<email>",
    "phoneNumberMobile": "<phoneNumberMobile>",
    "phoneNumberWork": "<phoneNumberWork>"
  }
}
```

### `PUT` /contact/{id}

Update contact.

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
    "isoAlpha3Code": "<isoAlpha3Code>",
    "isoNumericCode": "<isoNumericCode>"
  },
  "pho
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
    "email": "<email>",
    "phoneNumberMobile": "<phoneNumberMobile>",
    "phoneNumberWork": "<phoneNumberWork>"
  }
}
```

## Common usage patterns

```bash
# Create contact on customer
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/contact" -d '{"firstName":"Kari","lastName":"Hansen","email":"kari@acme.no","customer":{"id":123}}'
```
