# Tripletex AI Accounting Agent

AI agent for NM i AI 2026 — receives accounting task prompts in 7 languages and executes them via the Tripletex API.

## Setup

```bash
uv sync
```

## Run

```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000
```

## API Spec Extraction

### The problem

The Tripletex OpenAPI spec has 546 endpoints and is 3.5MB. That's way too large to put in an LLM context window. But our agent needs to know which endpoints exist and exactly which fields to send in each API call — otherwise it guesses, gets 422 errors, and loses efficiency points.

### The solution: two files

We extract the OpenAPI spec into two purpose-built files using `specs/build_registry.py`:

#### `specs/index.md` (~800 lines, ~18K tokens)

A markdown table with one line per endpoint. Just method, path, and a short summary.

```
| POST | `/employee`              | Create one employee.                    |
| GET  | `/customer`              | Find customers corresponding with data. |
| PUT  | `/invoice/{id}/:payment` | Update invoice with payment information. |
```

**How the agent uses it:** Always loaded in the system prompt. When the agent reads a task like "Opprett en ansatt med navn Ola Nordmann", it scans this index to find `POST /employee`. Think of it as a table of contents.

#### `specs/registry.json` (~2MB)

A JSON file where each key is `"METHOD /path"` and the value contains everything the agent needs to make that API call correctly:

```json
{
  "POST /employee": {
    "summary": "Create one employee.",
    "tags": ["employee"],
    "request_body": {
      "properties": {
        "firstName":  { "type": "string" },
        "lastName":   { "type": "string" },
        "email":      { "type": "string" },
        "userType":   { "type": "string", "enum": ["STANDARD", "EXTENDED", "NO_ACCESS"] },
        "department": { "type": "object", "properties": { "id": { "type": "integer" } }, "_ref": "Department" }
      }
    },
    "response": { "type": "single", "schema_ref": "ResponseWrapperEmployee" }
  }
}
```

**How the agent uses it:** Loaded on-demand. After the agent picks `POST /employee` from the index, it loads this entry to know the exact fields, types, and enums to send. The `_ref` tells it that `department` is a link to another entity — just send `{"id": 123}`, not the full department object.

**What's in each entry:**
- `request_body` — The fields you can send in POST/PUT requests, with types and enums
- `query_params` — The `?key=value` parameters for GET/action endpoints (search filters, pagination)
- `response` — Whether the response wraps data in `.value` (single) or `.values` (list)
- `content_type: "multipart/form-data"` — Present on file upload endpoints, marks which field is the binary upload

### How the extraction works

The raw OpenAPI spec uses `$ref` pointers everywhere (e.g. `"$ref": "#/components/schemas/Employee"`). We resolve these inline so the registry is self-contained. The key rules:

- **Object `$ref`** (e.g. `customer` pointing to the Customer schema) → Stubbed to `{"id": <int>}`. When you link an entity in a Tripletex POST/PUT, you only send its ID, never the full object.
- **Array `$ref`** (e.g. `orderLines` pointing to OrderLine schema) → Fully resolved. Arrays are inline child creations — the agent needs all writable fields (product, quantity, unitPrice, etc.).
- **`readOnly` fields** → Stripped. These are server-generated (id, version, displayName) and must never be sent in requests.
- **Circular references** → Detected via ancestor tracking, gracefully degraded to id-only stubs.
- **Multipart/form-data** → Extracted separately for file upload endpoints, with binary fields clearly marked.

### Rebuild

```bash
uv run python specs/build_registry.py
```

## Deploy

```bash
./deploy.sh
```
