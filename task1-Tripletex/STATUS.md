# Tripletex Agent — Status (2026-03-21 03:10)

## What was done

### Full agent rebuild
Rebuilt the agent from scratch combining best parts of two prior approaches:
- **Architecture**: Single LLM planning call → code execution loop (no multi-agent pipeline)
- **Framework**: Agents SDK for planning, litellm for fix calls
- **Model**: `gemini/gemini-3.1-pro-preview` via LitellmModel

### Files created
```
agent/
├── orchestrator.py     — Plan + execute (replaced pipeline.py + toolcaller.py)
├── client.py           — HTTP client with time budget, placeholder resolution, state
├── validator.py        — Pre-validates payloads against registry schemas
├── file_handler.py     — PDF/image decoding for LLM vision input
├── context.py          — Registry loading + schema rendering
├── config.py           — Model config
├── logging_config.py   — Structured logging
└── knowledgebase.md    — Merged domain knowledge (proven workflows)
```

### Key fixes from log analysis

| Fix | Impact |
|-----|--------|
| Salary: `rate` required on ALL specs (not `amount`) | Salary transactions no longer 422 |
| "i bruk" / "already exists" → auto GET existing entity | Products/projects/employees with duplicate numbers auto-recover |
| Unique project numbers in knowledgebase | Projects no longer fail on number collision |
| Disabled schema re-planning | Saves 20-30s per task, eliminates alias mismatch bugs |
| Dimension: `dimensionName` not `name`, document index→field mapping | Dimension creation works |
| Temperature 1.0 for Gemini 3 models | Avoids infinite loops per litellm warning |
| Action endpoint sanitization (/:payment, /:invoice, /:createCreditNote) | Body fields auto-moved to query params |
| Voucher posting field whitelist | Prevents invalid fields causing 422s |

### Verified working (sandbox)

| Task type | Status | Time |
|-----------|--------|------|
| T01 Employee (+ entitlements + employment) | ✓ PASS | ~20s |
| T02 Customer (+ address) | ✓ PASS | ~6s |
| T03 Supplier | ✓ PASS | ~6s |
| T04 Product (with VAT) | ✓ PASS | ~10s |
| T05 Departments (multiple) | ✓ PASS | ~8s |
| T06 Multi-line invoice (mixed VAT) | ✓ PASS | ~63s |
| T07 Order → Invoice → Payment | ✓ PASS | ~33s |
| T09 Register payment on invoice | ✓ PASS | ~27s |
| T09b Reverse payment (bank return) | ✓ PASS | ~23s |
| T10 Credit note | ✓ PASS | ~56s |
| T11 Create project | ✓ PASS | ~23s |
| T12 Fixed price project + milestone | ✓ PASS | ~52s |

## Still open / known issues

### VAT type IDs are sandbox-dependent
Our persistent sandbox rejects vatType id=3 (25%), id=31 (15%), id=5 (0%) on products. The LLM fix_payload retries with different IDs and usually succeeds, but wastes 5-10s per product. Competition sandboxes (blank) may have different valid IDs. The knowledgebase has correct IDs for standard Tripletex setups — if they fail, the LLM falls back to `GET /ledger/vatType`.

### Salary needs active employment in period
`POST /salary/transaction` requires the employee to have an active employment covering the salary month. Our sandbox employee (Lars Berg) has a future start date so salary fails. In competition, the evaluator sets up the employee correctly. The agent DOES correctly look up employment (`GET /employee/employment`) — it just can't create one for the right period if it doesn't exist.

### Travel expense: costs require separate POST calls
The agent sometimes tries to inline costs in `POST /travelExpense` which fails because `costs.paymentType` and `costs.amountCurrencyIncVat` are required. The knowledgebase documents the correct multi-step workflow (create expense → get categories/rates → post per diem → post costs separately), but the LLM doesn't always follow it. Could add sanitization to strip inline costs.

### Voucher posting sometimes fails
The voucher sanitizer correctly whitelists posting fields, but the API sometimes returns "Et bilag kan ikke registreres uten posteringer" even when postings are present. Root cause unclear — may be invalid account IDs, voucherType, or dimension references. The dimension→freeAccountingDimensionN mapping is documented but the LLM doesn't always use the correct index.

### Planning speed
Single planning call takes 8-35s depending on complexity. For a 5-minute timeout, this leaves 4+ minutes for execution which is usually enough. But complex tasks (10+ steps) can approach the budget. No re-planning means we rely on the knowledgebase quality for correctness.

### Hourly billing (T13) invoice step
The project + timesheet part works, but converting to an invoice often hits the bank account error ("Faktura kan ikke opprettes før selskapet har registrert et bankkontonummer"). This is a sandbox/company config issue, not an agent bug. The order + timesheet are still scored.

## Scoreboard mapping

| Competition task | Type | Expected score |
|-----------------|------|----------------|
| 01 Employee | Tier 1 | Should be ~2.0 now (entitlements fixed) |
| 02 Customer | Tier 1 | 2.0 (already good) |
| 03 Supplier | Tier 1 | 2.0 (already good) |
| 04 Product | Tier 1 | Should improve (VAT retry works) |
| 05 Departments | Tier 1 | Should be ~2.0 (departmentNumber included) |
| 06 Multi-line invoice | Tier 2 | Should score now (was 0) |
| 07 Order→Invoice→Payment | Tier 2 | Should improve significantly (was 0.29) |
| 09 Payment/Reversal | Tier 2 | Should stay ~2.8+ (already decent) |
| 11 Project creation | Tier 2 | Should score now (was 0) |
| 12 Fixed price project | Tier 2 | Should score now (was 0) |
| 13 Hourly billing | Tier 2 | Partial (invoice blocked by bank acct) |
| 17 Create+send invoice | Tier 2 | Should improve (was 0.92) |

## Next steps to improve score
1. **Deploy and submit** — the rebuilt agent needs to be deployed to Cloud Run
2. **Travel expense sanitization** — strip inline costs, force separate POST /travelExpense/cost calls
3. **Voucher posting debugging** — test with known-good account IDs and voucherTypes
4. **Tier 3 tasks** — opens Saturday, unknown task types (bank reconciliation from CSV, error correction, year-end closing)
5. **Speed optimization** — the planning prompt is ~15KB (knowledgebase + index). Could trim further
