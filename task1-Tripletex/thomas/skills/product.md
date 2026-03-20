# product

Tripletex API endpoints for managing product resources.

## Endpoints

### `GET` /product

Find products corresponding with sent data.

**Query parameters:**
- `number`: DEPRECATED. List of product numbers (Integer only)
- `ids`: List of IDs
- `productNumber`: List of valid product numbers
- `name`: Containing
- `ean`: Equals
- `isInactive`: Equals
- `isStockItem`: Equals
- `isSupplierProduct`: Equals
- `supplierId`: Equals
- `currencyId`: Equals

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

### `POST` /product

Create new product.

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
  "displayNumber": "<displayNumber>",
  "description": "<description>",
  "orderLineDescription": "<orderLineDescription>",
  "ean": "<ean>",
  "elNumber": "<elNumber>",
  "nrfNumber": "<nrfNumber>"
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
    "displayNumber": "<displayNumber>",
    "description": "<description>",
    "orderLineDescription": "<orderLineDescription>",
    "ean": "<ean>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>"
  }
}
```

### `GET` /product/discountGroup

Find discount groups corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
- `number`: List of IDs
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

### `GET` /product/discountGroup/{id}

Get discount group by ID.

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
    "nameAndNumber": "<nameAndNumber>"
  }
}
```

### `GET` /product/external

[BETA] Find external products corresponding with sent data. The sorting-field is not in use on this endpoint.

**Query parameters:**
- `name`: Containing
- `wholesaler`: Wholesaler
- `organizationNumber`: Wholesaler organization number. Mandatory if Wholesaler is not selected. If Wholesaler is selected, 
- `elNumber`: List of valid el numbers
- `nrfNumber`: List of valid nrf numbers
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

### `GET` /product/external/{id}

[BETA] Get external product by ID.

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
    "displayName": "<displayName>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>",
    "costExcludingVatCurrency": 0.0,
    "priceExcludingVatCurrency": 0.0,
    "priceIncludingVatCurrency": 0.0,
    "isInactive": true
  }
}
```

### `GET` /product/group

Find product group with sent data. Only available for Logistics Basic.

**Query parameters:**
- `id`: List of IDs
- `name`: Containing
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

### `POST` /product/group

Create new product group. Only available for Logistics Basic.

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
  "displayName": "<displayName>",
  "parentGroup": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
    "isDeletable": true
  },
  "isDeletable": true
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
    "displayName": "<displayName>",
    "isDeletable": true
  }
}
```

### `PUT` /product/group/list

Update a list of product groups. Only available for Logistics Basic.

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

### `POST` /product/group/list

Add multiple products groups. Only available for Logistics Basic.

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

### `DELETE` /product/group/list

Delete multiple product groups. Only available for Logistics Basic.

**Query parameters:**
- `ids` (required): ID of the elements

### `GET` /product/group/query

Wildcard search. Only available for Logistics Basic.

**Query parameters:**
- `query`: Containing
- `name`: Containing
- `fields`: Fields filter pattern
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

### `GET` /product/group/{id}

Find product group by ID. Only available for Logistics Basic.

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
    "displayName": "<displayName>",
    "isDeletable": true
  }
}
```

### `PUT` /product/group/{id}

Update product group. Only available for Logistics Basic.

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
  "displayName": "<displayName>",
  "parentGroup": {
    "id": 0,
    "version": 0,
    "changes": [
      "..."
    ],
    "url": "<url>",
    "name": "<name>",
    "displayName": "<displayName>",
    "isDeletable": true
  },
  "isDeletable": true
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
    "displayName": "<displayName>",
    "isDeletable": true
  }
}
```

### `DELETE` /product/group/{id}

Delete product group. Only available for Logistics Basic.

### `GET` /product/groupRelation

Find product group relation with sent data. Only available for Logistics Basic.

**Query parameters:**
- `id`: List of IDs
- `productId`: List of IDs
- `productGroupId`: List of IDs
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

### `POST` /product/groupRelation

Create new product group relation. Only available for Logistics Basic.

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
  "productGroup": {
    "id": 0,
    "version": 0,
    "c
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
    "url": "<url>"
  }
}
```

### `POST` /product/groupRelation/list

Add multiple products group relations. Only available for Logistics Basic.

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

### `DELETE` /product/groupRelation/list

Delete multiple product group relations. Only available for Logistics Basic.

### `GET` /product/groupRelation/{id}

Find product group relation by ID. Only available for Logistics Basic.

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
    "url": "<url>"
  }
}
```

### `DELETE` /product/groupRelation/{id}

Delete product group relation. Only available for Logistics Basic.

### `GET` /product/inventoryLocation

Find inventory locations by product ID. Only available for Logistics Basic.

**Query parameters:**
- `productId`: List of IDs
- `inventoryId`: List of IDs
- `isMainLocation`: Equals
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

### `POST` /product/inventoryLocation

Create new product inventory location. Only available for Logistics Basic.

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
    "isMainLocation": true,
    "isInactive": true,
    "stockOfGoods": 0.0
  }
}
```

### `PUT` /product/inventoryLocation/list

Update multiple product inventory locations. Only available for Logistics Basic.

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

### `POST` /product/inventoryLocation/list

Add multiple product inventory locations. Only available for Logistics Basic.

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

### `GET` /product/inventoryLocation/{id}

Get inventory location by ID. Only available for Logistics Basic.

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
    "isMainLocation": true,
    "isInactive": true,
    "stockOfGoods": 0.0
  }
}
```

### `PUT` /product/inventoryLocation/{id}

Update product inventory location. Only available for Logistics Basic.

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
    "isMainLocation": true,
    "isInactive": true,
    "stockOfGoods": 0.0
  }
}
```

### `DELETE` /product/inventoryLocation/{id}

Delete product inventory location. Only available for Logistics Basic.

### `PUT` /product/list

Update a list of products.

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

### `POST` /product/list

Add multiple products.

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

### `GET` /product/logisticsSettings

Get logistics settings for the logged in company.

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
    "hasWarehouseLocation": true,
    "showOnboardingWizard": true,
    "moduleSuggestedProductNumber": true,
    "suggestedProductNumber": "<suggestedProductNumber>",
    "purchaseOrderDefaultComment": "<purchaseOrderDefaultComment>",
    "rackbeatAgreementNumber": "<rackbeatAgreementNumber>",
    "moduleBring": true
  }
}
```

### `PUT` /product/logisticsSettings

Update logistics settings for the logged in company.

**Request body example:**
```json
{
  "id": 0,
  "version": 0,
  "changes": [
    "..."
  ],
  "url": "<url>",
  "hasWarehouseLocation": true,
  "showOnboardingWizard": true,
  "moduleSuggestedProductNumber": true,
  "suggestedProductNumber": "<suggestedProductNumber>",
  "purchaseOrderDefaultComment": "<purchaseOrderDefaultComment>",
  "rackbeatAgreementNumber": "<rackbeatAgreementNumber>",
  "moduleBring": true
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
    "hasWarehouseLocation": true,
    "showOnboardingWizard": true,
    "moduleSuggestedProductNumber": true,
    "suggestedProductNumber": "<suggestedProductNumber>",
    "purchaseOrderDefaultComment": "<purchaseOrderDefaultComment>",
    "rackbeatAgreementNumber": "<rackbeatAgreementNumber>",
    "moduleBring": true
  }
}
```

### `GET` /product/productPrice

Find prices for a product. Only available for Logistics Basic.

**Query parameters:**
- `productId` (required): Equals
- `fromDate`: From and including
- `toDate`: To and excluding
- `showOnlyLastPrice`: If showOnlyLastPrice is true, fromDate and toDate are ignored and only last price of the product is 
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

### `GET` /product/supplierProduct

Find products corresponding with sent data.

**Query parameters:**
- `productId`: Id of product to find supplier products for.
- `resaleIds`: List of IDs
- `vendorId`: Id of vendor to find supplier products for.
- `query`: Containing
- `isInactive`: Equals
- `productGroupId`: List of IDs
- `count`: Number of elements to return
- `fields`: Fields filter pattern
- `targetCurrencyId`: The target currency ID for price conversion.
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

### `POST` /product/supplierProduct

Create new supplierProduct.

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
  "displayName": "<displayName>",
  "number": "<number>",
  "description": "<description>",
  "ean": "<ean>",
  "costExcludingVatCurrency": 0.0,
  "cost": 0.0,
  "priceExcludingVatCurrency": 0.0
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
    "displayName": "<displayName>",
    "number": "<number>",
    "description": "<description>",
    "ean": "<ean>",
    "costExcludingVatCurrency": 0.0,
    "cost": 0.0,
    "priceExcludingVatCurrency": 0.0
  }
}
```

### `POST` /product/supplierProduct/getSupplierProductsByIds

Find the products by ids. Method was added as a POST because GET request header has a maximum size that we can exceed with customers that a lot of products.

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

### `PUT` /product/supplierProduct/list

Update a list of supplierProduct.

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

### `POST` /product/supplierProduct/list

Create list of new supplierProduct.

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

### `GET` /product/supplierProduct/{id}

Get supplierProduct by ID.

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
    "displayName": "<displayName>",
    "number": "<number>",
    "description": "<description>",
    "ean": "<ean>",
    "costExcludingVatCurrency": 0.0,
    "cost": 0.0,
    "priceExcludingVatCurrency": 0.0
  }
}
```

### `PUT` /product/supplierProduct/{id}

Update supplierProduct.

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
  "displayName": "<displayName>",
  "number": "<number>",
  "description": "<description>",
  "ean": "<ean>",
  "costExcludingVatCurrency": 0.0,
  "cost": 0.0,
  "priceExcludingVatCurrency": 0.0
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
    "displayName": "<displayName>",
    "number": "<number>",
    "description": "<description>",
    "ean": "<ean>",
    "costExcludingVatCurrency": 0.0,
    "cost": 0.0,
    "priceExcludingVatCurrency": 0.0
  }
}
```

### `DELETE` /product/supplierProduct/{id}

Delete supplierProduct.

### `GET` /product/unit

Find product units corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Names
- `nameShort`: Short names
- `commonCode`: Common codes
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

### `POST` /product/unit

Create new product unit.

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
  "displayNameShort": "<displayNameShort>",
  "name": "<name>",
  "nameEN": "<nameEN>",
  "nameShort": "<nameShort>",
  "nameShortEN": "<nameShortEN>",
  "commonCode": "<commonCode>",
  "isDeletable": true
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
    "displayNameShort": "<displayNameShort>",
    "name": "<name>",
    "nameEN": "<nameEN>",
    "nameShort": "<nameShort>",
    "nameShortEN": "<nameShortEN>",
    "commonCode": "<commonCode>",
    "isDeletable": true
  }
}
```

### `PUT` /product/unit/list

Update list of product units.

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

### `POST` /product/unit/list

Create multiple product units.

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

### `GET` /product/unit/master

Find product units master corresponding with sent data.

**Query parameters:**
- `id`: List of IDs
- `name`: Names
- `nameShort`: Short names
- `commonCode`: Common codes
- `peppolName`: Peppol names
- `peppolSymbol`: Peppol symbols
- `isInactive`: Inactive units
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

### `GET` /product/unit/master/{id}

Get product unit master by ID.

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
    "nameShort": "<nameShort>",
    "commonCode": "<commonCode>",
    "peppolName": "<peppolName>",
    "peppolSymbol": "<peppolSymbol>",
    "isInactive": true
  }
}
```

### `GET` /product/unit/query

Wildcard search.

**Query parameters:**
- `query`: Containing
- `count`: Number of elements to return
- `fields`: Fields filter pattern
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

### `GET` /product/unit/{id}

Get product unit by ID.

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
    "displayNameShort": "<displayNameShort>",
    "name": "<name>",
    "nameEN": "<nameEN>",
    "nameShort": "<nameShort>",
    "nameShortEN": "<nameShortEN>",
    "commonCode": "<commonCode>",
    "isDeletable": true
  }
}
```

### `PUT` /product/unit/{id}

Update product unit.

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
  "displayNameShort": "<displayNameShort>",
  "name": "<name>",
  "nameEN": "<nameEN>",
  "nameShort": "<nameShort>",
  "nameShortEN": "<nameShortEN>",
  "commonCode": "<commonCode>",
  "isDeletable": true
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
    "displayNameShort": "<displayNameShort>",
    "name": "<name>",
    "nameEN": "<nameEN>",
    "nameShort": "<nameShort>",
    "nameShortEN": "<nameShortEN>",
    "commonCode": "<commonCode>",
    "isDeletable": true
  }
}
```

### `DELETE` /product/unit/{id}

Delete product unit by ID.

### `GET` /product/{id}

Get product by ID.

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
    "displayNumber": "<displayNumber>",
    "description": "<description>",
    "orderLineDescription": "<orderLineDescription>",
    "ean": "<ean>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>"
  }
}
```

### `PUT` /product/{id}

Update product.

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
  "displayNumber": "<displayNumber>",
  "description": "<description>",
  "orderLineDescription": "<orderLineDescription>",
  "ean": "<ean>",
  "elNumber": "<elNumber>",
  "nrfNumber": "<nrfNumber>"
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
    "displayNumber": "<displayNumber>",
    "description": "<description>",
    "orderLineDescription": "<orderLineDescription>",
    "ean": "<ean>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>"
  }
}
```

### `DELETE` /product/{id}

Delete product.

### `POST` /product/{id}/image

Upload image to product. Existing image on product will be replaced if exists

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
    "displayNumber": "<displayNumber>",
    "description": "<description>",
    "orderLineDescription": "<orderLineDescription>",
    "ean": "<ean>",
    "elNumber": "<elNumber>",
    "nrfNumber": "<nrfNumber>"
  }
}
```

### `DELETE` /product/{id}/image

Delete image.

## Common usage patterns

```bash
# List products
curl -u "0:$TOKEN" "$URL/product?fields=id,name,number,priceExcludingVat"

# Create product
curl -X POST -u "0:$TOKEN" -H "Content-Type: application/json" \
  "$URL/product" -d '{"name":"Konsulenttime","number":1001,"priceExcludingVat":1500.00}'
```
