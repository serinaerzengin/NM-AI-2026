# Tripletex AI Accounting Agent — CLAUDE.md

## Project Overview
AI agent for NM i AI 2026 competition. Receives accounting task prompts (30 types, 7 languages, 8 data variants each = 56 variants per task) and executes them against a Tripletex sandbox API. Deployed on Google Cloud Run.

## Architecture
- **Tool-calling agent loop** using `openai` SDK pointed at Gemini's OpenAI-compatible endpoint
- LLM receives tools (tripletex_get, tripletex_post, tripletex_put, tripletex_delete), calls them iteratively
- No hardcoded playbooks — the LLM decides what to do based on the system prompt guidance

## Key Files
- `api.py` — FastAPI server with /health and /solve endpoints
- `agent.py` — Core agent loop, tool definitions, response truncation
- `system_prompt.py` — System prompt with endpoint index, workflows, and rules
- `apply_fixes.py` — Silent payload corrections + lazy setup (bank account, division, employment)
- `tripletex_client.py` — HTTP client with Basic auth
- `file_handler.py` — PDF/image/CSV/XLSX processing
- `deploy.sh` — Cloud Run deployment script
- `docs/production_log_analysis.md` — Exhaustive analysis of production failures and fixes

## MOST IMPORTANT — Task Variants
Each of the 30 task types has **56 variants** (7 languages × 8 data sets). When we submit online, we get a **random variant we've almost certainly never seen before**. This means:
- A fix that works for one specific prompt/data set on our local sandbox may NOT work for the other 7 variants
- **ALL fixes must be GENERAL** — describe the workflow pattern (e.g. "find invoice → register payment → book agio/disagio"), NOT specific values (e.g. "use account 8060 for the 2000 EUR invoice")
- Testing on sandbox validates the CODE works, but does NOT guarantee the LLM will handle a different variant correctly
- The LLM must understand the PATTERN, not memorize a specific solution
- If a fix works on sandbox but fails online, the fix is too specific — make it more general

## Critical Constraints
- **300 second timeout** — competition hard limit (we use Cloud Run, not Cloudflare)
- **BETA endpoints return 403** — confirmed by competition organizers. Do NOT use endpoints marked [BETA] in OpenAPI spec
- **Scoring**: correctness (field-by-field) × tier multiplier + efficiency bonus (fewer calls, zero errors)
- **Fresh sandbox per submission** — no state carries over

## Important Patterns
- When modifying `system_prompt.py`: Keep workflows general. Don't hardcode specific amounts, names, or IDs. Describe the PATTERN that works for all 8 data variants. Ask yourself: "Would this guidance help the LLM if the amounts, names, language, and account numbers were completely different?"
- When modifying `apply_fixes.py`: Only add fixes for consistently wrong field names/structures that appear across ALL variants, not task-specific logic.
- Sandbox validation confirms the code works, but the REAL test is online with a variant you haven't seen. If it fails online after passing sandbox, the fix is too specific.
- Log analysis is at `docs/production_log_analysis.md` — update it when investigating issues.
- Every log line is tagged with `[req_id]` for filtering concurrent requests.
- When analyzing production logs: look for PATTERNS across runs, not individual fixes. A problem that appears in 2+ different variants is a real problem. A problem in 1 run might be variant-specific noise.

## Commands
```bash
# Run locally
uv run uvicorn api:app --host 0.0.0.0 --port 8080

# Deploy
bash deploy.sh

# Check logs
gcloud run services logs read tripletex-agent --region europe-north1 --project ai-nm26osl-1813 --limit 500

# Filter by request
grep "\[abc12345\]" logs.txt
```
