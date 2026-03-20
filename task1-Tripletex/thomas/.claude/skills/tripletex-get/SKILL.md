---
name: tripletex-get
description: GET request to Tripletex API to list or search entities (employees, customers, products, etc.)
---

Use the Bash tool to make a GET request to the Tripletex API.

## Usage
```bash
curl -s -u "0:$SESSION_TOKEN" "$BASE_URL{path}?{params}"
```

## Examples

List employees:
```bash
curl -s -u "0:$SESSION_TOKEN" "$BASE_URL/employee?fields=id,firstName,lastName,email"
```

Search customer by name:
```bash
curl -s -u "0:$SESSION_TOKEN" "$BASE_URL/customer?name=Acme&fields=id,name,email&count=10"
```

Get entity by ID:
```bash
curl -s -u "0:$SESSION_TOKEN" "$BASE_URL/employee/123?fields=*"
```

## Response format
- List: `{"fullResultSize": N, "values": [...]}`
- Single: `{"value": {...}}`

## Tips
- Always use `fields` to limit response size
- Use `fields=*` to discover all fields
- Use `count` and `from` for pagination
