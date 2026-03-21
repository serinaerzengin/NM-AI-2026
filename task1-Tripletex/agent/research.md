# Preprocessing Pipeline — Research & Design

Architecture for the preprocessing stage before the tool-calling agent.
Each step is backed by specific research findings.

```
Raw User Prompt (Norwegian/multilingual, possibly with files)
    ↓
[Step 1: Translator] — detect language, translate to English, preserve domain terms
    ↓
[Step 2: Query Rewriter] — resolve ambiguity, ground to Tripletex API vocabulary
    ↓
[Step 3: Task Decomposer] — reads index.md (table of contents) to identify endpoints
    │                         outputs: ordered to-do list with dependencies
    ↓
[Step 4: Format as Structured Plan] — pulls specific entries from registry.json (the book)
    │                                   fills in params, request bodies, types
    ↓
Feed into Tool-Calling Agent (executor)
```

### Where the API specs fit

The specs act as a **two-phase retrieval system** — a pattern strongly supported by research on scalable tool selection:

- **`specs/index.md`** = Table of Contents (~800 lines, ~18K tokens, ~800 endpoints)
  - Lightweight: Method | Path | One-line summary
  - Small enough to always live in the system prompt (~18K tokens)
  - Used by **Step 3 (Task Decomposer)** to scan and identify which endpoints are needed
  - The decomposer never needs param details — just needs to know "POST /customer exists"

- **`specs/registry.json`** = The Book (~2MB, 800 entries with full schemas)
  - Each entry has: summary, tags, query_params (name, type, default, description), request_body (full property schema with types and enums), response schema ref
  - 277 endpoints have request_body (POST/PUT), 462 have query_params (GET/search)
  - Object `$ref` fields are stubbed to `{"id": <int>, "_ref": "EntityName"}` — agent just sends IDs to link entities
  - Array `$ref` fields are fully resolved inline — these are child creations (e.g. orderLines) where all writable fields are needed
  - `readOnly` fields and server-assigned fields (id, version, changes, url) are already stripped — agent can safely use the schema as a template without risking 422 errors from sending server-only fields
  - `content_type: "multipart/form-data"` marks file upload endpoints with binary field indicators
  - 483 `_ref` stubs across the registry — each one is an implicit dependency hint (need to resolve that entity's ID first)
  - Too large to fit entirely in context — pulled **on demand** for only the endpoints selected in Step 3
  - Used by **Step 4 (Format as Structured Plan)** to fill in exact params, required fields, enum values

```
Step 3 reads index.md:  "I need POST /employee and GET /customer"
                              ↓
Step 4 pulls from registry.json:  registry["POST /employee"] → {request_body: {firstName, lastName, email, ...}}
                                  registry["GET /customer"]  → {query_params: [{name, type}, ...]}
                              ↓
Structured plan with correct params ready for executor
```

---

## Step 1: Translator

**Purpose:** Detect the source language (nb, nn, en, es, pt, de, fr) and translate to English while preserving all accounting terms, entity names, numbers, dates, and formatting.

**Why a dedicated step:**
- Prompts arrive in 7 languages with 56 variants per task
- Norwegian accounting terminology (e.g. "kundefordring", "saldoliste", "bilag") must map correctly to English equivalents that the downstream steps understand
- Mixing translation with intent extraction causes task interference — the "Let Me Speak Freely?" finding (Tam et al., EMNLP 2024) showed 27%+ accuracy drops when models juggle multiple output concerns simultaneously
  - Source: https://arxiv.org/abs/2408.02442

**What the research says:**
- The NLT paper (Johnson et al., Oct 2025) demonstrated that **decoupling tasks into single-responsibility stages** improves accuracy by 18.4pp across 6,400 trials. Translation is the clearest case for isolation — it has one job
  - Source: https://arxiv.org/abs/2510.14453
- TUMS (May 2025) showed that a dedicated Intent Recognizer as the first pipeline stage improved hard benchmarks by **50.6%**. Translation is a prerequisite for correct intent recognition when inputs are multilingual
  - Source: https://arxiv.org/abs/2505.08402

**Design rules:**
- Output ONLY the English translation — no commentary, no JSON wrapper, no labels
- Preserve Norwegian proper nouns exactly (company names, person names)
- Preserve numeric formats, dates, currency amounts verbatim
- If input is already English, return unchanged
- Keep it as plain natural language (not JSON) — structured output degrades translation quality

**Relevant for our case:**
- The competition scores field-by-field (names, emails, amounts). A mistranslated name = lost points
- Norwegian characters (æ, ø, å) work fine in Tripletex API calls — don't transliterate them

---

## Step 2: Query Rewriter

**Purpose:** Take the English translation and rewrite it to be unambiguous, grounded in Tripletex API vocabulary, and explicit about what entities and actions are needed.

**Why this step matters:**
- Raw prompts use natural language that doesn't map 1:1 to API operations
- Example: "Register a payment for the invoice" is ambiguous — do we need to create the invoice first? Which customer? What payment type?
- Query reformulation before tool selection improves tool matching precision dramatically

**What the research says:**
- **Dynamic ReAct** (Gaurav et al., Sep 2025) — decomposing into "atomic queries" focused on single actions reduced tool loading by **50%** while maintaining accuracy
  - Source: https://arxiv.org/html/2509.20386v1
- **INQURE** (Nicolai et al., VLDB DATAI 2025) — intent-based query rewriting that preserves "obtainable insights" even when restructuring. Separating intent identification from query translation resolves vague terminology more robustly
  - Source: https://arxiv.org/abs/2511.20419
- **Anthropic context engineering** (Sep 2025) — up to **54% improvement** with proper context engineering. Recommends grounding queries to the tool vocabulary before the agent sees them
  - Source: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- **PLAY2PROMPT** (ACL 2025) — optimizing tool descriptions and input phrasing in zero-shot settings improves performance without adding examples. Better descriptions > more examples
  - Source: https://arxiv.org/abs/2503.14432

**What the rewriter should do:**
1. **Ground to API vocabulary** — map natural language terms to Tripletex entity types:
   - "worker" / "staff member" / "ansatt" → `employee`
   - "bill" / "faktura" → `invoice`
   - "travel claim" / "reiseregning" → `travelExpense`
   - "supplier" / "leverandør" → `supplier`
2. **Resolve implicit references** — "create an invoice for Acme" implies we need to find or create the customer first
3. **Make dependencies explicit** — "register a payment" requires: customer exists → order exists → invoice exists → payment
4. **Expand abbreviations and shorthand** — "admin" → "account administrator role"
5. **Preserve exact values** — names, emails, amounts, dates must pass through unchanged

**Output format:** Natural language with structural markers. NOT JSON (based on the structured-output-degrades-reasoning finding). Example:

```
Task: Create a new employee and assign them as account administrator.
Entities: employee (firstName: "Ola", lastName: "Nordmann", email: "ola@example.org")
Actions: POST /employee with administrator role = true
Prerequisites: none
```

**What NOT to do here:**
- Don't ask the rewriter to output a full execution plan — that's Step 3's job
- Don't force JSON output — it causes 17-27% reasoning degradation (Tam et al., 2024; ACL 2025 anonymous submission on structured output and creativity)
- Don't include few-shot examples of API calls in the rewriter prompt — it'll parrot the examples instead of reasoning about the actual query

---

## Step 3: Task Decomposer

**Purpose:** Take the rewritten query and decompose it into an ordered to-do list of concrete steps, with explicit dependencies. Uses `index.md` as a table of contents to identify which endpoints are needed — without loading full param schemas.

**Why a to-do list:**
- Multi-step Tripletex tasks require strict ordering (can't create an invoice without a customer and order first)
- The scoring system penalizes 4xx errors — planning before calling avoids trial-and-error
- Efficiency bonus requires minimal API calls — a good plan avoids unnecessary GETs

**What the research says:**
- **Plan-and-Act** (Erdogan et al., ICML 2025) — separating planning from execution achieves **92% accuracy vs ReAct's 85%**, and is especially better on long-horizon tasks
  - Source: https://arxiv.org/abs/2503.09572
- **Beyond ReAct** (Wei et al., AAAI 2026) — generates a DAG plan in a single pass. Qwen3-8B with planning **beats GPT-4 with ReAct** (59.8% vs 48.2%) using only 2.29 average inference steps
  - Source: https://arxiv.org/abs/2511.10037
- **PEAR benchmark** (Oct 2025) — "a weak planner degrades performance more severely than a weak executor." The planning step is the most critical component
  - Source: https://arxiv.org/abs/2510.07505
- **ACONIC** (Columbia, Oct 2025) — models decomposition as constraint satisfaction. Claude accuracy improved from 49.3% → **58.1%**, LLaMA-3-70B from 21.5% → **36.5%**
  - Source: https://arxiv.org/html/2510.07772v1
- **Routine framework** (Jul 2025) — hybrid NL + structured step plans pushed GPT-4o from **41.1% → 96.3%**. Each step has: number, name, description, tool, type
  - Source: https://arxiv.org/abs/2507.14447
- **Towards Data Science** (Leung, Dec 2025) — dedicated article confirming to-do lists help agents track progress in multi-tool coordination
  - Source: https://towardsdatascience.com/how-agents-plan-tasks-with-to-do-lists/

**How index.md is used here:**

The decomposer receives `index.md` (~800 lines, ~18K tokens) in its system prompt. This is small enough to always be present. The decomposer scans it to match intent to endpoints:

```
Decomposer sees rewritten query: "Create employee Ola Nordmann with admin role"
Decomposer scans index.md and finds:
  | POST | /employee | Create one employee |
  | GET  | /employee | Find employees corresponding with sent data |
Decomposer outputs plan referencing these endpoints by path only.
```

**Why index.md and not registry.json here:**
- index.md is ~800 lines / ~18K tokens — small enough to live permanently in the system prompt
- registry.json is ~2MB / 800 detailed entries — too large, would dilute reasoning
- The decomposer only needs to know WHAT endpoints exist, not their param schemas
- This mirrors the **Tool-to-Agent Retrieval** pattern (Lumer et al., Nov 2025): coarse retrieval first (scan summaries), fine-grained retrieval later (pull details for selected tools)
  - Source: https://arxiv.org/abs/2511.01854
- Also matches **TOOLQP** (Fang & Glass, Jan 2026): "standard single-shot dense retrievers fail for complex requests over massive tool libraries" — iterative, multi-step retrieval over tool descriptions works better
  - Source: https://arxiv.org/abs/2601.07782
- And **Dynamic ReAct** (Gaurav et al., Sep 2025): reducing loaded tools by 50% through targeted retrieval maintained accuracy while cutting cost
  - Source: https://arxiv.org/html/2509.20386v1

**Output format:** Numbered step list in natural language with dependency markers. Endpoint paths identified from index.md, but no params yet.

Example for "Create an invoice for customer Acme AS with product 'Consulting' at 1500 NOK":

```
Step 1: Search for existing customer "Acme AS"
  → endpoint: GET /customer
  → depends on: none

Step 2: If customer not found, create customer "Acme AS"
  → endpoint: POST /customer
  → depends on: Step 1

Step 3: Create product "Consulting" at 1500 NOK
  → endpoint: POST /product
  → depends on: none (can run parallel with Step 1-2)

Step 4: Create order linking customer and product
  → endpoint: POST /order
  → depends on: Step 2, Step 3

Step 5: Create invoice from order
  → endpoint: POST /invoice
  → depends on: Step 4
```

**Design principles (from Agent-Oriented Planning, ICLR 2025):**
- **Solvability** — each step can be resolved by a single API call
- **Completeness** — all necessary work is covered
- **Non-redundancy** — no duplicate effort
  - Source: https://arxiv.org/abs/2410.02189

**Common Tripletex task patterns to inform decomposition:**

| Pattern | Steps | Key dependency |
|---------|-------|----------------|
| Create single entity | 1 step | none |
| Create with linking | 2-3 steps | entity must exist before linking |
| Create invoice | 3-5 steps | customer → product → order → invoice |
| Register payment | 4-6 steps | customer → order → invoice → payment |
| Modify existing | 2 steps | GET to find ID → PUT to update |
| Delete entity | 2 steps | GET to find ID → DELETE |

---

## Step 4: Format as Structured Plan (registry.json lookup)

**Purpose:** Take the natural language to-do list from Step 3, pull the detailed schemas for each referenced endpoint from `registry.json`, and produce a structured plan with correct params, types, and required fields that the executor can run deterministically.

**This is the "open the book to the right page" step.**

**Why a separate formatting step:**
- The task decomposer should reason freely in natural language (better accuracy)
- The executor needs parseable structure with correct field names and types (reliable execution)
- Decoupling these follows the "generate freely, then structure" pattern validated by multiple papers
- Loading only the needed registry entries (typically 2-6 endpoints out of 800) keeps context focused

**How registry.json is used here:**

After Step 3 outputs a plan referencing endpoints by path (e.g. `POST /employee`, `GET /customer`), this step:

1. **Extracts the endpoint paths** from the to-do list
2. **Looks up each one in registry.json** by key (e.g. `registry["POST /employee"]`)
3. **Injects the schema details** into the plan — request_body properties, query_params, types, enums, required fields

Example — Step 3 said `POST /employee`, registry.json returns:
```json
{
  "summary": "Create one employee.",
  "tags": ["employee"],
  "request_body": {
    "type": "object",
    "properties": {
      "firstName": {"type": "string"},
      "lastName": {"type": "string"},
      "email": {"type": "string"},
      "phoneNumberMobile": {"type": "string"},
      "dateOfBirth": {"type": "string"},
      "department": {
        "type": "object",
        "properties": {"id": {"type": "integer", "format": "int64"}},
        "_ref": "Department"
      },
      "userType": {"type": "string", "enum": ["STANDARD", "EXTENDED", "NO_ACCESS"]},
      ...
    }
  },
  "response": {"type": "single", "schema_ref": "ResponseWrapperEmployee"}
}
```

Key details the registry provides that prevent errors:
- `_ref: "Department"` → tells executor it needs a department ID, not a department object. This is an **implicit dependency**: may need `GET /department` first to resolve the ID
- `enum: ["STANDARD", "EXTENDED", "NO_ACCESS"]` → executor knows exactly which values are valid
- `readOnly` fields already stripped → safe to use schema as template, no risk of sending `id` or `version`
- `response.type: "single"` → response is in `.value`, not `.values` (list endpoints use `.values`)

This step can be **code, not an LLM call** — it's a deterministic lookup + merge:
```python
import json

def enrich_plan(steps: list[dict], registry: dict) -> list[dict]:
    """Pull registry schemas for each step's endpoint."""
    for step in steps:
        key = f"{step['method']} {step['endpoint']}"
        if key in registry:
            step["schema"] = registry[key]
    return steps
```

Or if using an LLM for this step, feed it ONLY the relevant registry entries (not the full 1.3MB), letting it fill in the param values from the rewritten query.

**What the research says:**
- **SLOT** (EMNLP 2025 Industry) — a lightweight post-processing layer transforms unstructured LLM output into structured format, achieving **99.5% schema accuracy**
  - Source: https://aclanthology.org/2025.emnlp-industry.32/
- **Deco-G** (Oct 2025) — decouples format adherence from task solving using separate probabilistic model
  - Source: https://arxiv.org/abs/2510.03595
- **LLMCompiler** (ICML 2024) — generates a DAG of tasks with dependencies, dispatches in parallel where possible. Achieves **3.7x latency speedup** and **~9% accuracy improvement** vs ReAct
  - Source: https://github.com/SqueezeAILab/LLMCompiler
- **AutoTool** (Jia & Li, Nov 2025) — builds a Tool Inertia Graph from historical trajectories to predict tool transitions, **bypassing LLM inference for predictable selections**. 15-25% reduction in LLM calls. Our registry lookup is the same idea: don't ask the LLM to guess param names when we have the schema
  - Source: https://arxiv.org/abs/2511.14650

**Output format:** Each step enriched with the actual schema from registry.json.

```yaml
plan:
  - step: 1
    action: "Search for customer named Acme AS"
    method: GET
    endpoint: "/customer"
    params:                          # ← from registry["GET /customer"].query_params
      name: "Acme AS"
      fields: "id,name,email"
      count: 1
    depends_on: []

  - step: 2
    action: "Create customer if not found"
    method: POST
    endpoint: "/customer"
    body:                            # ← from registry["POST /customer"].request_body
      name: "Acme AS"
      email: "post@acme.no"
      isCustomer: true
    depends_on: [1]
    condition: "only if step 1 returns empty results"

  - step: 3
    action: "Create product Consulting"
    method: POST
    endpoint: "/product"
    body:                            # ← from registry["POST /product"].request_body
      name: "Consulting"
      priceExcludingVat: 1500
      currency: {"id": <NOK_id>}
    depends_on: []
```

**Why this works:**
- The executor gets exact field names (`firstName` not `first_name`), correct types (`boolean` not `"true"`), valid enum values
- No guessing, no 422 validation errors from wrong field names — directly from the schema
- `readOnly` fields already stripped by build_registry.py — agent can't accidentally send server-only fields like `id`, `version`, `changes`, `url`
- `_ref` stubs surface hidden dependencies — if the schema says `"department": {"_ref": "Department"}`, executor knows to resolve the department ID first
- `response.type` tells executor whether to read `.value` (single entity) or `.values` (list) from the API response
- Only 2-6 registry entries loaded per task instead of all 800 — focused context
- This is the ONE place where structured format (YAML/JSON) is appropriate — the executor needs it

**The two-phase retrieval pattern summarized:**

| Phase | Input | Tool | Output | Size in context |
|-------|-------|------|--------|-----------------|
| Coarse (Step 3) | Rewritten query | `index.md` (~18K tokens) | Endpoint paths + ordering | ~800 lines (always in system prompt) |
| Fine (Step 4) | Selected endpoints | `registry.json` entries | Full schemas w/ types, enums, `_ref` stubs | ~2-6 entries (on-demand, tiny) |

This avoids the failure mode identified by TOOLQP: "disconnect between abstract user goals and technical API documentation." index.md bridges the goal→endpoint gap, registry.json bridges the endpoint→params gap.

---

## Cross-Cutting Concerns

### Few-Shot Examples: 3-5 max, dynamically selected

- **LangChain study** (Jul 2024) — Claude 3 Haiku went from 11% → **75%** with just 3 examples. 3 semantically similar examples performed as well as all 13
  - Source: https://blog.langchain.com/few-shot-prompting-to-improve-tool-calling-performance/
- **ToolACE** (ICLR 2025) — few-shot actually **fell short of zero-shot** for fine-tuned models. Examples misled models into hallucinating tools from examples
  - Source: https://arxiv.org/abs/2409.00920
- **Frontiers of CS** (2026) — increasing examples per tool produces **mixed effects**. Quality >> quantity
  - Source: https://link.springer.com/article/10.1007/s11704-025-41365-6
- **Anthropic guidance** (2025) — "Include 3-5 examples for best results." Diverse, relevant, wrapped in `<example>` tags
  - Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

**Recommendation:** Include 3-5 examples of common Tripletex task patterns (create employee, create invoice, modify entity) in the Task Decomposer prompt. Select dynamically based on similarity to the current query if possible.

### Preserving Sequential Order

- **DAG-based plans** (GAP, NeurIPS 2025) — model dependencies as directed edges, enabling both strict ordering and parallelism
  - Source: https://arxiv.org/abs/2510.25320
- **DynTaskMAS** (ICAPS 2025) — dynamic task graph with continuous updates, **21-33% reduction in execution time**
  - Source: https://arxiv.org/abs/2503.07675
- For our case, a simple numbered list with `depends_on` is sufficient — Tripletex tasks rarely exceed 6 steps

### Prompt Format

- Use **XML tags or Markdown headers** to delimit sections in agent prompts
- Tool definitions as **typed JSON schemas** (from registry.json)
- Reasoning and planning in **natural language**
- The **Routine framework** format (step number + name + description + tool + type in NL) gave the best results: **41% → 96%** on GPT-4o
  - Source: https://arxiv.org/abs/2507.14447

---

## Sources (All)

| Paper | Venue | Date | URL |
|-------|-------|------|-----|
| "Let Me Speak Freely?" (Tam et al.) | EMNLP 2024 Industry | Aug 2024 | https://arxiv.org/abs/2408.02442 |
| Natural Language Tools (Johnson et al.) | arXiv | Oct 2025 | https://arxiv.org/abs/2510.14453 |
| TUMS: Multi-structure Handlers | arXiv | May 2025 | https://arxiv.org/abs/2505.08402 |
| Dynamic ReAct (Gaurav et al.) | arXiv | Sep 2025 | https://arxiv.org/html/2509.20386v1 |
| INQURE (Nicolai et al.) | VLDB DATAI 2025 | Nov 2025 | https://arxiv.org/abs/2511.20419 |
| Anthropic context engineering | Blog | Sep 2025 | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| PLAY2PROMPT (Fang et al.) | ACL 2025 Findings | Mar 2025 | https://arxiv.org/abs/2503.14432 |
| Plan-and-Act (Erdogan et al.) | ICML 2025 | Mar 2025 | https://arxiv.org/abs/2503.09572 |
| Beyond ReAct (Wei et al.) | AAAI 2026 | Nov 2025 | https://arxiv.org/abs/2511.10037 |
| PEAR benchmark (Dong et al.) | arXiv | Oct 2025 | https://arxiv.org/abs/2510.07505 |
| ACONIC (Zhou et al.) | arXiv | Oct 2025 | https://arxiv.org/html/2510.07772v1 |
| Routine framework (Zeng et al.) | arXiv | Jul 2025 | https://arxiv.org/abs/2507.14447 |
| To-do lists for agents (Leung) | Towards Data Science | Dec 2025 | https://towardsdatascience.com/how-agents-plan-tasks-with-to-do-lists/ |
| Agent-Oriented Planning (Li et al.) | ICLR 2025 | Oct 2024 | https://arxiv.org/abs/2410.02189 |
| SLOT (Shen et al.) | EMNLP 2025 Industry | 2025 | https://aclanthology.org/2025.emnlp-industry.32/ |
| Deco-G (Deng et al.) | arXiv | Oct 2025 | https://arxiv.org/abs/2510.03595 |
| LLMCompiler (Kim et al.) | ICML 2024 | 2024 | https://github.com/SqueezeAILab/LLMCompiler |
| AutoTool (Jia & Li) | arXiv | Nov 2025 | https://arxiv.org/abs/2511.14650 |
| Tool-to-Agent Retrieval (Lumer et al.) | arXiv | Nov 2025 | https://arxiv.org/abs/2511.01854 |
| TOOLQP (Fang & Glass) | arXiv | Jan 2026 | https://arxiv.org/abs/2601.07782 |
| GAP: Graph-Based Agent Planning | NeurIPS 2025 | Oct 2025 | https://arxiv.org/abs/2510.25320 |
| DynTaskMAS (Yu et al.) | ICAPS 2025 | Mar 2025 | https://arxiv.org/abs/2503.07675 |
| LangChain few-shot study | Blog | Jul 2024 | https://blog.langchain.com/few-shot-prompting-to-improve-tool-calling-performance/ |
| ToolACE | ICLR 2025 | Sep 2024 | https://arxiv.org/abs/2409.00920 |
| Investigating in-context tool use (Zheng et al.) | Frontiers of CS | 2026 | https://link.springer.com/article/10.1007/s11704-025-41365-6 |
| Anthropic prompting best practices | Docs | 2025 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices |
