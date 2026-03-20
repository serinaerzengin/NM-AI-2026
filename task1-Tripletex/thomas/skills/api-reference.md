# Tripletex API v2 Reference

## Authentication
- Basic Auth: username `0`, password = session token
- Header: `Authorization: Basic <base64(0:sessionToken)>`

## Date formats
- **Date**: `YYYY-MM-DD` (ISO 8601)
- **DateTime**: `YYYY-MM-DDThh:mm:ss` (ISO 8601)

## PUT = Partial Update
- Tripletex uses PUT with optional fields instead of PATCH
- Only include fields you want to update
- Include the `version` field from GET response to prevent conflicts

## Actions & Summaries
- **Actions** use `:` prefix: `/hours/123/:approve`, `/invoice/123/:payment`
- **Summaries** use `>` prefix: `/hours/>thisWeeksBillables`

## Fields parameter
Select which fields to return:
- `?fields=id,name,email` — specific fields
- `?fields=*` — all fields
- `?fields=project(*)` — expand sub-resource
- `?fields=project(name)` — specific sub-field
- `?fields=*,activity(name),employee(*)` — mix

## Sorting
- `?sorting=date` — ascending
- `?sorting=-date` — descending (prefix with -)
- `?sorting=project.name,-date` — multiple, sub-object

## Pagination
- `?from=0&count=100` — offset and limit
- Default count varies by endpoint

## Searching
Search via query params on GET endpoints. Categories:
- **range**: `dateFrom=2026-01-01&dateTo=2026-12-31`
- **in**: `id=1,2,3` (comma-separated IDs)
- **exact**: `email=test@example.com`
- **like**: `name=Acme` (partial match)

## Response envelopes

### Multiple values (list/search)
```json
{
  "fullResultSize": 123,
  "from": 0,
  "count": 100,
  "versionDigest": "...",
  "values": [{...}, {...}]
}
```

### Single value (get by ID / create / update)
```json
{
  "value": {...}
}
```

### Error response
```json
{
  "status": 422,
  "code": 15000,
  "message": "Human readable message",
  "developerMessage": "Technical detail",
  "validationMessages": [
    {"field": "name", "message": "Required field"}
  ],
  "requestId": "abc-123"
}
```

## Status codes
| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Success |
| 201 | Created | POST created entity, check `value.id` |
| 204 | No Content | DELETE or action succeeded, no body |
| 400 | Bad Request | Check params, filter syntax |
| 401 | Unauthorized | Check auth — username `0`, password = token |
| 403 | Forbidden | Missing permissions/entitlements |
| 404 | Not Found | Wrong path or entity doesn't exist |
| 409 | Conflict | Edit conflict — include `version` in PUT |
| 422 | Validation Error | Read `validationMessages` for which fields are wrong |
| 429 | Rate Limited | Wait and retry |

## Version field
- All persisted resources have a `version` field
- Include it in PUT requests to prevent overwriting concurrent changes
- Get it from the GET response before updating

## Important patterns
1. **Create**: POST returns `{"value": {"id": 123, ...}}` — save the ID
2. **Update**: GET first (to get `version`), then PUT with `id` + `version` + changed fields
3. **Delete**: DELETE by ID, returns 204
4. **Search then act**: GET with search params to find entity, then use its ID
5. **Linked entities**: Use `{"id": 123}` format for references (e.g. `"customer": {"id": 456}`)

## Common pitfalls
- Missing `isCustomer: true` when creating customers
- Not providing `userType` when creating employees
- Not finding/creating a department before creating employees (some setups require it)
- Invoice requires: customer + order (with order lines) first
- Forgetting `version` field on PUT causes 409 Conflict
- Empty `values` array means no results — broaden your search
