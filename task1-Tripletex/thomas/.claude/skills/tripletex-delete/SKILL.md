---
name: tripletex-delete
description: DELETE request to Tripletex API to remove entities
---

Use the Bash tool to make a DELETE request to the Tripletex API.

## Usage
```bash
curl -s -X DELETE -u "0:$SESSION_TOKEN" "$BASE_URL{path}/{id}"
```

## Examples

Delete travel expense:
```bash
curl -s -X DELETE -u "0:$SESSION_TOKEN" "$BASE_URL/travelExpense/123"
```

## Tips
- GET first to find the ID
- Returns 204 No Content on success
