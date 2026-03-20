# Implementation Plan — Preprocessing Pipeline

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ /solve endpoint receives: prompt, files, tripletex_credentials      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         ┌─────────────────────▼──────────────────────┐
         │  Step 1: TRANSLATOR (LLM agent)            │
         │                                            │
         │  Receives:  raw prompt (any language)      │
         │  Returns:   English plain text             │
         │                                            │
         │  Knows NOTHING about:                      │
         │   - Tripletex API                          │
         │   - registry.json / index.md               │
         │   - files, credentials                     │
         └─────────────────────┬──────────────────────┘
                               │ plain English string
         ┌─────────────────────▼──────────────────────┐
         │  Step 2: QUERY REWRITER (LLM agent)        │
         │                                            │
         │  Receives:  English translation only       │
         │  Returns:   clarified NL text              │
         │                                            │
         │  Knows NOTHING about:                      │
         │   - index.md / registry.json               │
         │   - specific endpoints or params           │
         │   - files, credentials                     │
         └─────────────────────┬──────────────────────┘
                               │ clarified English string
         ┌─────────────────────▼──────────────────────┐
         │  Step 3: TASK DECOMPOSER (LLM agent)       │
         │                                            │
         │  Receives:  clarified query + index.md     │
         │  Returns:   ordered to-do list (NL)        │
         │             with endpoint paths            │
         │                                            │
         │  Knows NOTHING about:                      │
         │   - registry.json (no param schemas)       │
         │   - original language / raw prompt         │
         │   - files, credentials                     │
         └─────────────────────┬──────────────────────┘
                               │ to-do list with endpoint paths
         ┌─────────────────────▼──────────────────────┐
         │  Step 4: PLAN FORMATTER (code, not LLM)    │
         │                                            │
         │  Receives:  to-do list + registry.json     │
         │  Returns:   structured plan with schemas   │
         │                                            │
         │  Knows NOTHING about:                      │
         │   - original prompt / translation          │
         │   - rewriter reasoning                     │
         │   - index.md (already consumed in Step 3)  │
         └─────────────────────┬──────────────────────┘
                               │ structured plan (JSON/YAML)
         ┌─────────────────────▼──────────────────────┐
         │  Step 5: EXECUTOR (LLM agent + tools)      │
         │                                            │
         │  Receives:  structured plan + credentials  │
         │             + files (if any)               │
         │  Returns:   nothing (side effects on API)  │
         │                                            │
         │  Knows NOTHING about:                      │
         │   - how the plan was made                  │
         │   - original prompt language               │
         │   - index.md / full registry.json          │
         └────────────────────────────────────────────┘
```

---

## Data Isolation Contract

Each step has a strict input/output boundary. No agent receives information it doesn't need.

| Step | Input | Output | Does NOT receive |
|------|-------|--------|------------------|
| 1. Translator | `raw_prompt: str` | `english_text: str` | files, credentials, index.md, registry.json |
| 2. Rewriter | `english_text: str` | `clarified_text: str` | raw_prompt, files, credentials, index.md, registry.json |
| 3. Decomposer | `clarified_text: str` + `index.md` (in system prompt) | `todo_list: str` (NL with endpoint paths) | raw_prompt, english_text, files, credentials, registry.json |
| 4. Formatter | `todo_list: str` + `registry.json` (code lookup) | `plan: list[PlanStep]` | raw_prompt, all prior text, index.md, credentials |
| 5. Executor | `plan: list[PlanStep]` + `credentials` + `files` | API side effects | raw_prompt, all prior text, index.md, full registry.json |

**Why strict isolation:**
- Prevents task interference (research: 27% accuracy drop when models juggle multiple concerns)
- Each agent has a focused context window — no dilution from irrelevant data
- Credentials never touch preprocessing agents (Steps 1-4) — only the executor needs them
- Files only reach the executor — preprocessors work from text description only

---

## Step 1: Translator

### Agent definition

```python
translator_agent = Agent(
    name="Translator",
    model=model,
    instructions="""You are a translation specialist.

The user will provide a prompt in one of these languages:
Norwegian Bokmål, Nynorsk, English, Spanish, Portuguese, German, or French.

Your job:
1. If the prompt is already in English, return it unchanged.
2. Otherwise, translate it to fluent English.

Rules:
- Preserve all proper nouns exactly (person names, company names)
- Preserve all numbers, dates, currency amounts, email addresses verbatim
- Preserve Norwegian characters (æ, ø, å) in proper nouns — do NOT transliterate
- Preserve accounting terminology accurately
- Return ONLY the English translation — no commentary, no labels, no JSON""",
)
```

### Input → Output contract

```
IN:  "Opprett en ansatt med navn Ola Nordmann, ola@example.org. Han skal være kontoadministrator."
OUT: "Create an employee named Ola Nordmann, ola@example.org. He should be an account administrator."
```

```
IN:  "Create an employee named Ola Nordmann with email ola@example.org"
OUT: "Create an employee named Ola Nordmann with email ola@example.org"
```

### Implementation

```python
async def step1_translate(raw_prompt: str) -> str:
    result = await Runner.run(translator_agent, input=raw_prompt)
    return result.final_output
```

---

## Step 2: Query Rewriter

### Agent definition

```python
rewriter_agent = Agent(
    name="QueryRewriter",
    model=model,
    instructions="""You are a query clarification specialist for an accounting system.

You receive an English task description. Rewrite it to be unambiguous and explicit.

What to do:
- Map informal terms to standard accounting entity names:
  "worker"/"staff member" → employee
  "bill" → invoice
  "travel claim" → travel expense
  "supplier"/"vendor" → supplier
  "admin" → account administrator
- Make implicit actions explicit (e.g. "invoice for Acme" implies customer must exist)
- Spell out what entities need to be created, modified, or looked up
- Preserve ALL exact values: names, emails, amounts, dates — copy them character-for-character

What NOT to do:
- Do NOT output JSON
- Do NOT reference specific API endpoints or paths
- Do NOT generate an execution plan or numbered steps
- Do NOT add information that wasn't in the original

Output format: plain English text structured as:
Task: [one sentence summary]
Entities: [entity type (field: "value", field: "value"), ...]
Actions: [what needs to happen in plain English]
Prerequisites: [what must exist first, or "none"]""",
)
```

### Input → Output contract

```
IN:  "Create an employee named Ola Nordmann, ola@example.org. He should be an account administrator."

OUT:
Task: Create a new employee and assign account administrator role.
Entities: employee (firstName: "Ola", lastName: "Nordmann", email: "ola@example.org", administrator: true)
Actions: Create the employee with administrator privileges.
Prerequisites: none
```

```
IN:  "Create an invoice for customer Acme AS for consulting services, 1500 NOK."

OUT:
Task: Create an invoice for an existing or new customer with one product line.
Entities: customer (name: "Acme AS"), product (name: "consulting services", price: 1500, currency: NOK), invoice
Actions: Find or create customer "Acme AS". Create product. Create order linking customer and product. Create invoice from order.
Prerequisites: customer must exist before order; order must exist before invoice
```

### Implementation

```python
async def step2_rewrite(english_text: str) -> str:
    result = await Runner.run(rewriter_agent, input=english_text)
    return result.final_output
```

### What this agent does NOT see
- The original Norwegian/multilingual prompt (only the English translation)
- index.md or registry.json (it doesn't pick endpoints — that's Step 3's job)
- Files or credentials

---

## Step 3: Task Decomposer

### Agent definition

```python
import pathlib

INDEX_MD = (pathlib.Path(__file__).parent.parent / "specs" / "index.md").read_text()

decomposer_agent = Agent(
    name="TaskDecomposer",
    model=model,
    instructions=f"""You are a task planning specialist for the Tripletex accounting API.

You receive a clarified task description. Your job is to decompose it into an ordered
list of concrete API steps, using the endpoint index below to identify which endpoints to call.

<endpoint_index>
{INDEX_MD}
</endpoint_index>

Rules:
- Each step must map to exactly ONE API call (one endpoint)
- Include the HTTP method and path for each step (from the index above)
- Mark dependencies between steps with "depends on: Step N"
- If steps have no dependency on each other, note they can run in parallel
- Do NOT guess parameter names or request body fields — just identify the endpoint
- Do NOT include authentication details
- Think about what entities must exist before others can be created

Output format — numbered steps in plain text:

Step 1: [description]
  → endpoint: [METHOD /path]
  → depends on: [none | Step N, Step M]

Step 2: [description]
  → endpoint: [METHOD /path]
  → depends on: [Step 1]

...""",
)
```

### Input → Output contract

```
IN:
Task: Create an invoice for an existing or new customer with one product line.
Entities: customer (name: "Acme AS"), product (name: "consulting services", price: 1500, currency: NOK), invoice
Actions: Find or create customer "Acme AS". Create product. Create order linking customer and product. Create invoice from order.
Prerequisites: customer must exist before order; order must exist before invoice

OUT:
Step 1: Search for existing customer "Acme AS"
  → endpoint: GET /customer
  → depends on: none

Step 2: If not found, create customer "Acme AS"
  → endpoint: POST /customer
  → depends on: Step 1

Step 3: Create product "consulting services" at 1500 NOK
  → endpoint: POST /product
  → depends on: none

Step 4: Create order linking customer to product
  → endpoint: POST /order/orderline
  → depends on: Step 2, Step 3

Step 5: Create invoice from order
  → endpoint: POST /invoice
  → depends on: Step 4
```

### Implementation

```python
async def step3_decompose(clarified_text: str) -> str:
    result = await Runner.run(decomposer_agent, input=clarified_text)
    return result.final_output
```

### What this agent does NOT see
- Original prompt or translation (only the clarified rewrite)
- registry.json (no param schemas — just the index table of contents)
- Files or credentials
- How the rewriter arrived at its output

---

## Step 4: Plan Formatter

### This is CODE, not an LLM

Deterministic: parse the to-do list, look up registry entries, merge.

```python
import json
import re
import pathlib
from dataclasses import dataclass, field

REGISTRY_PATH = pathlib.Path(__file__).parent.parent / "specs" / "registry.json"

@dataclass
class PlanStep:
    step: int
    action: str
    method: str
    endpoint: str
    schema: dict          # from registry.json — request_body or query_params
    depends_on: list[int]
    condition: str = ""   # e.g. "only if step 1 returns empty"

@dataclass
class ExecutionPlan:
    steps: list[PlanStep]
    raw_todo: str         # original NL from decomposer (for debugging only)


def load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def parse_todo(todo_text: str) -> list[dict]:
    """Parse the NL to-do list into step dicts with method, endpoint, depends_on."""
    steps = []
    current = None

    for line in todo_text.strip().splitlines():
        line = line.strip()

        # Match "Step N: description"
        step_match = re.match(r"Step\s+(\d+):\s*(.+)", line)
        if step_match:
            if current:
                steps.append(current)
            current = {
                "step": int(step_match.group(1)),
                "action": step_match.group(2).strip(),
                "method": "",
                "endpoint": "",
                "depends_on": [],
                "condition": "",
            }
            continue

        if not current:
            continue

        # Match "→ endpoint: METHOD /path"
        ep_match = re.match(r"→\s*endpoint:\s*(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)", line, re.I)
        if ep_match:
            current["method"] = ep_match.group(1).upper()
            current["endpoint"] = ep_match.group(2)
            continue

        # Match "→ depends on: Step 1, Step 3" or "none"
        dep_match = re.match(r"→\s*depends on:\s*(.+)", line, re.I)
        if dep_match:
            dep_text = dep_match.group(1).strip()
            if dep_text.lower() == "none":
                current["depends_on"] = []
            else:
                current["depends_on"] = [
                    int(d) for d in re.findall(r"Step\s+(\d+)", dep_text)
                ]
            continue

        # Capture any condition text (e.g. "If not found, ...")
        if line.lower().startswith("if ") or "condition" in line.lower():
            current["condition"] = line

    if current:
        steps.append(current)

    return steps


def enrich_with_registry(steps: list[dict], registry: dict) -> list[PlanStep]:
    """Look up each endpoint in registry.json and attach its schema."""
    enriched = []
    for s in steps:
        key = f"{s['method']} {s['endpoint']}"
        schema = registry.get(key, {})
        enriched.append(PlanStep(
            step=s["step"],
            action=s["action"],
            method=s["method"],
            endpoint=s["endpoint"],
            schema=schema,
            depends_on=s["depends_on"],
            condition=s.get("condition", ""),
        ))
    return enriched


def step4_format(todo_text: str) -> ExecutionPlan:
    """Parse to-do list and enrich with registry schemas."""
    registry = load_registry()
    parsed = parse_todo(todo_text)
    steps = enrich_with_registry(parsed, registry)
    return ExecutionPlan(steps=steps, raw_todo=todo_text)
```

### Input → Output contract

```
IN:  the NL to-do list string from Step 3

OUT: ExecutionPlan with steps like:
  PlanStep(
      step=2,
      action='If not found, create customer "Acme AS"',
      method="POST",
      endpoint="/customer",
      schema={
          "summary": "Create one customer.",
          "request_body": {
              "properties": {
                  "name": {"type": "string"},
                  "email": {"type": "string"},
                  "isCustomer": {"type": "boolean"},
                  "invoiceEmail": {"type": "string"},
                  ...
              }
          },
          "response": {"type": "single", "schema_ref": "ResponseWrapperCustomer"}
      },
      depends_on=[1],
      condition="If not found"
  )
```

### What this code does NOT see
- Original prompt, translation, or rewriter output
- Credentials or files
- index.md (already consumed by Step 3 — not needed here)

### What it provides to Step 5
- The schema for ONLY the endpoints in the plan (2-6 entries, not all 800)
- Correct field names, types, enums from registry.json
- `_ref` stubs that hint at entity linking (just send `{"id": N}`)
- `response.type` so executor knows to read `.value` vs `.values`

---

## Step 5: Executor

### Agent definition (sketch — this is the downstream agent, not preprocessing)

The executor receives the structured plan + credentials + files. It does NOT receive the original prompt, translation, rewrite, or index.md. Its job is to execute the plan step by step, calling the Tripletex API.

```python
executor_agent = Agent(
    name="Executor",
    model=model,
    tools=[tripletex_api_tool],  # HTTP tool with auth baked in
    instructions="""You are an API execution agent for Tripletex.

You receive a structured execution plan. Execute each step in order,
respecting the depends_on relationships.

For each step you have:
- method and endpoint to call
- schema with exact field names, types, and enums to use
- depends_on telling you which steps must complete first

Rules:
- Use ONLY the field names from the schema — do not guess or invent fields
- For _ref fields (linked entities), send only {"id": <int>} with the ID from a previous step's response
- Read responses: .value for single entities, .values for lists
- If a step has a condition (e.g. "only if step 1 returns empty"), check before executing
- Pass IDs from previous step responses into subsequent steps (e.g. customer_id from Step 1 into Step 4)
- Do NOT make API calls that are not in the plan""",
)
```

### What this agent receives
- `plan.steps` — the enriched PlanStep objects with schemas
- `base_url` and `session_token` — Tripletex API credentials
- `files` — decoded file attachments (if the task includes them)

### What this agent does NOT see
- Original prompt (any language)
- Translation or rewrite text
- index.md or full registry.json
- How or why the plan was constructed

---

## Full Pipeline Orchestration

```python
async def run(
    prompt: str,
    base_url: str,
    session_token: str,
    files: list | None = None,
) -> None:
    """Full pipeline: translate → rewrite → decompose → format → execute."""

    # Step 1: Translate (LLM) — sees only raw prompt
    english = await step1_translate(prompt)

    # Step 2: Rewrite (LLM) — sees only english text
    clarified = await step2_rewrite(english)

    # Step 3: Decompose (LLM) — sees clarified text + index.md (in system prompt)
    todo = await step3_decompose(clarified)

    # Step 4: Format (code) — sees todo text + registry.json
    plan = step4_format(todo)

    # Step 5: Execute (LLM + tools) — sees plan + credentials + files
    await step5_execute(plan, base_url, session_token, files)
```

### Data flow diagram — what crosses each boundary

```
prompt ──→ [Step 1] ──→ english ──→ [Step 2] ──→ clarified ──→ [Step 3] ──→ todo ──→ [Step 4] ──→ plan ──→ [Step 5]
                                                                   ↑                     ↑                     ↑
                                                              index.md            registry.json          credentials
                                                          (system prompt)        (code lookup)             + files
```

No arrows cross more than one boundary. Each step's output is the ONLY input to the next step (plus its static reference data).

---

## Open Questions

1. **Should Step 2 (Rewriter) see index.md too?** Currently no — it grounds to entity vocabulary, not endpoints. But if it struggles to distinguish "order" (sales order) from "order" (sort order), scanning the index might help. Test without first.

2. **Should Steps 1+2 be merged?** They're both LLM calls on plain text. Merging saves one LLM round-trip (~1-2s). But research says single-responsibility stages are more accurate. Test both — if translation quality stays high when combined, merge for speed.

3. **Can Step 3 output be parsed reliably?** The NL format with `→ endpoint:` and `→ depends on:` markers is simple regex. If the LLM deviates from format, we could add a lightweight validation pass. Alternatively, use XML tags (`<step>`, `<endpoint>`, `<depends_on>`) which LLMs follow more reliably.

4. **File handling** — where do files get processed? Currently files go straight to the executor. But some tasks include PDFs with data (invoice amounts, names) that the preprocessor needs. May need a Step 0 (file extractor) or pass file summaries into Step 2.

5. **Error recovery** — if the executor hits a 422, should it replan? Current design is plan-once-execute. Adding a feedback loop (executor → decomposer) adds complexity but could recover from bad plans. Start without it.
