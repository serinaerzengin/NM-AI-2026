# Task 1 — Tripletex AI Accounting Agent

AI agent that completes accounting tasks in Tripletex via the v2 REST API.

## Stack

- **LLM**: Gemini (via LiteLLM) — configurable in `thomas/agent.py`
- **Framework**: OpenAI Agents SDK (Agent, Runner, function_tool)
- **Tools**: 40 typed endpoints auto-generated from the Tripletex OpenAPI spec
- **Skills**: Per-category API docs + language mappings + API reference
- **Server**: FastAPI on Cloud Run

## Setup

### 1. Clone and install

```bash
cd task1-Tripletex
uv sync
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Add your keys:

```
GEMINI_API_KEY=your-gemini-key        # From https://aistudio.google.com/apikey
OPENAI_API_KEY=sk-...                  # Optional, if using OpenAI models
PROJECT=your-gcp-project-id            # For Cloud Run deploy
GOOGLE_MAIL=your@gcplab.me
GOOGLE_PASSWORD=...

# Sandbox (for local testing)
TRIPLETEX_BASE_URL=https://kkpqfuj-amager.tripletex.dev/v2
TRIPLETEX_SESSION_TOKEN=your-sandbox-token
```

Get your sandbox credentials at https://app.ainm.no/submit/tripletex

### 3. Test locally

```bash
# Quick test against sandbox
source .env
uv run python -c "
import asyncio
from thomas.agent import run
asyncio.run(run(
    prompt='Opprett en kunde med navn Test AS og e-post test@test.no.',
    base_url='$TRIPLETEX_BASE_URL',
    session_token='$TRIPLETEX_SESSION_TOKEN',
))
"
```

### 4. Run evals

```bash
# All 52 Tier 1 cases
node thomas/eval/run_eval.mjs

# Filter
node thomas/eval/run_eval.mjs --category employee
node thomas/eval/run_eval.mjs --lang de
node thomas/eval/run_eval.mjs --limit 5
node thomas/eval/run_eval.mjs --id t1_employee_01_nb
```

Requires `npm install @anthropic-ai/claude-agent-sdk dotenv` for the eval runner.

### 5. Deploy to Cloud Run

```bash
# Authenticate with GCP
gcloud auth login your@gcplab.me
gcloud config set project $PROJECT

# Deploy
./deploy.sh
```

Submit the Cloud Run URL at https://app.ainm.no/submit/tripletex

## Project structure

```
├── api.py                  # FastAPI /solve + /health endpoint
├── Dockerfile              # Cloud Run container
├── deploy.sh               # One-command deploy
├── core/
│   └── openapi_tools.py    # 40 typed tools from OpenAPI spec
├── thomas/
│   ├── agent.py            # Agent: system prompt + model + tools
│   ├── skills/             # Skill files (API docs per category)
│   │   ├── api-reference.md    # Auth, fields, sorting, errors
│   │   ├── languages.md        # 7-language term mappings
│   │   ├── employee.md         # Employee endpoints + examples
│   │   ├── customer.md         # Customer endpoints + examples
│   │   └── ...                 # product, invoice, order, etc.
│   └── eval/
│       ├── tier1_cases.jsonl   # 52 test cases
│       └── run_eval.mjs        # Eval runner
└── docs/
    ├── openapi.json            # Full Tripletex API spec (3.5MB)
    └── api-map.md              # Endpoint summary
```

## How it works

1. `/solve` receives a task prompt + Tripletex credentials
2. Agent gets 40 typed tools (create_employee, search_customers, etc.)
3. Skills are loaded as tool descriptions so the LLM knows field names and examples
4. System prompt includes API reference (auth, errors, patterns) and language mappings
5. Agent parses the prompt, calls the right tools, returns `{"status": "completed"}`

## Switching models

Edit `thomas/agent.py` line 9:

```python
# Gemini
MODEL = LitellmModel(model="gemini/gemini-3-flash-preview")

# OpenAI
MODEL = LitellmModel(model="gpt-4o-mini")

# Any LiteLLM-supported model
MODEL = LitellmModel(model="anthropic/claude-sonnet-4-20250514")
```

## Adding a new approach

1. Create a folder: `mkdir my_approach`
2. Add `my_approach/agent.py` with an `async def run(prompt, base_url, session_token, files)` function
3. Update `api.py`: `from my_approach.agent import run`
4. Redeploy
