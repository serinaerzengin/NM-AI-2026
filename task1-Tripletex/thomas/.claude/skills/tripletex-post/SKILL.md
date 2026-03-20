---
name: tripletex-post
description: POST request to Tripletex API to create new entities (employees, customers, invoices, etc.)
---

Use the Bash tool to make a POST request to the Tripletex API.

## Usage
```bash
curl -s -X POST -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL{path}" -d '{json_body}'
```

## Examples

Create employee:
```bash
curl -s -X POST -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL/employee" -d '{"firstName":"Ola","lastName":"Nordmann","email":"ola@example.com"}'
```

Create customer:
```bash
curl -s -X POST -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL/customer" -d '{"name":"Acme AS","email":"post@acme.no","isCustomer":true}'
```

Create product:
```bash
curl -s -X POST -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL/product" -d '{"name":"Konsulenttime","number":1001,"priceExcludingVat":1500.00}'
```

Create department:
```bash
curl -s -X POST -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL/department" -d '{"name":"Salg","departmentNumber":1}'
```

## Response format
`{"value": {"id": 123, ...}}`

## Tips
- Save the `id` from response to link entities later
- Some entities need prerequisites (invoice needs customer + order)
- Read error messages for missing required fields
