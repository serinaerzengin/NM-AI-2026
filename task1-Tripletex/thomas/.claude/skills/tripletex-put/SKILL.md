---
name: tripletex-put
description: PUT request to Tripletex API to update existing entities
---

Use the Bash tool to make a PUT request to the Tripletex API.

## Usage
```bash
curl -s -X PUT -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL{path}/{id}" -d '{json_body}'
```

## Examples

Update employee:
```bash
curl -s -X PUT -u "0:$SESSION_TOKEN" -H "Content-Type: application/json" "$BASE_URL/employee/123" -d '{"id":123,"firstName":"Ola","lastName":"Nordmann","email":"new@example.com"}'
```

## Tips
- Always include `id` in the body
- GET the entity first to know current state
- Include all required fields, not just changed ones
