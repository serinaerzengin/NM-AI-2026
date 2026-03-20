# customer

Tripletex API endpoints for managing customer resources.

## IMPORTANT: Customer vs Supplier

- **Customer** (kunde/client): set `"isCustomer": true`
- **Supplier** (leverandør/fournisseur/Lieferant/proveedor/fornecedor): set `"isSupplier": true`
- An entity can be BOTH customer and supplier

## IMPORTANT: Addresses

When a prompt includes an address, set it in `postalAddress`:
```json
{
  "name": "Acme AS",
  "isCustomer": true,
  "postalAddress": {
    "addressLine1": "Industriveien 56",
    "postalCode": "4611",
    "city": "Kristiansand"
  }
}
```

Norwegian address format: "Street Number, PostalCode City"
Example: "Kirkegata 132, 7010 Trondheim" → addressLine1="Kirkegata 132", postalCode="7010", city="Trondheim"

## Endpoints

### `GET` /customer

Find customers corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `customerAccountNumber`: List of customer numbers
- `organizationNumber`: Equals
- `email`: Equals
- `invoiceEmail`: Equals
- `customerName`: Name
- `phoneNumberMobile`: Phone number mobile
- `isInactive`: Equals
- `accountManagerId`: List of IDs
- `changedSince`: Only return elements that have changed since this date and time

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

### `POST` /customer

Create customer. Related customer addresses may also be created.

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
  "organizationNumber": "<organizationNumber>",
  "globalLocationNumber": 0,
  "supplierNumber": 0,
  "customerNumber": 0,
  "isSupplier": true,
  "isCustomer": true,
  "isInactive": true
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
    "organizationNumber": "<organizationNumber>",
    "globalLocationNumber": 0,
    "supplierNumber": 0,
    "customerNumber": 0,
    "isSupplier": true,
    "isCustomer": true,
    "isInactive": true
  }
}
```

### `GET` /customer/category

Find customer/supplier categories corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
- `number`: Equals
- `description`: Containing
- `type`: List of IDs
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

### `POST` /customer/category

Add new customer/supplier category.

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
  "type": 0,
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
    "type": 0,
    "displayName": "<displayName>"
  }
}
```

### `GET` /customer/category/{id}

Find customer/supplier category by ID.

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
    "type": 0,
    "displayName": "<displayName>"
  }
}
```

### `PUT` /customer/category/{id}

Update customer/supplier category.

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
  "type": 0,
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
    "type": 0,
    "displayName": "<displayName>"
  }
}
```

### `PUT` /customer/list

[BETA] Update multiple customers. Addresses can also be updated.

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

### `POST` /customer/list

[BETA] Create multiple customers. Related supplier addresses may also be created.

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

### `GET` /customer/{id}

Get customer by ID.

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
    "organizationNumber": "<organizationNumber>",
    "globalLocationNumber": 0,
    "supplierNumber": 0,
    "customerNumber": 0,
    "isSupplier": true,
    "isCustomer": true,
    "isInactive": true
  }
}
```

### `PUT` /customer/{id}

Update customer. 

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
  "organizationNumber": "<organizationNumber>",
  "globalLocationNumber": 0,
  "supplierNumber": 0,
  "customerNumber": 0,
  "isSupplier": true,
  "isCustomer": true,
  "isInactive": true
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
    "organizationNumber": "<organizationNumber>",
    "globalLocationNumber": 0,
    "supplierNumber": 0,
    "customerNumber": 0,
    "isSupplier": true,
    "isCustomer": true,
    "isInactive": true
  }
}
```

### `DELETE` /customer/{id}

[BETA] Delete customer by ID

## Common usage patterns

```bash
# List customers
curl -u "0:$TOKEN" "$URL/customer?fields=id,name,email"

# Create customer
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/customer" -d '{"name":"Acme AS","email":"post@acme.no","isCustomer":true}'

# Get customer by ID
curl -u "0:$TOKEN" "$URL/customer/456?fields=*"
```
