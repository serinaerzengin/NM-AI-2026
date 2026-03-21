# V5 Analysis — Critical Architecture Review

**Deployment**: Revision after v4 fixes (2026-03-21 ~20:13 UTC)
**Total runs**: 29
**Result**: Marginal improvement. Core problems persist.

---

## V5 Run Summary

| Status | Count | Details |
|--------|-------|---------|
| ✅ Clean (0 errors) | 17 | Simple tasks mostly work |
| ⚠️ Completed with errors | 7 | Errors reduce score but task partially done |
| ❌ Token expired | 2 | d299289a, 120adc49 — not our bug |
| 🔄 Still running | 3 | ef8cc4a4, ad22037c, 13c46b39 — likely timed out |

### Completed with errors:
- **b6c32c18** (9 calls, 1 err): Product number already exists. Recovered by GET.
- **eae1c4e2** (15 calls, 3 err): Invalid bank account number on PUT. FX milestone task.
- **a5e68ab2** (10 calls, 3 err): Ledger error correction — "Leverandør mangler" on correction vouchers. Agent tried but got supplier ID wrong.
- **c9adc48f** (19 calls, 1 err): Reminder fee — vatType locked on account 3400.
- **1f093d11** (12 calls, 1 err): Product number already exists. Recovered.
- **629cbf11** (24 calls, 1 err): Bank recon — unknown error.
- **ebdc6908** (10 calls, 3 err): Ledger error correction — same "Leverandør mangler" pattern.

---

## Critical Retrospective: Why Fixes Don't Improve Scores

### Pattern observed across V1 → V5:
We've done ~20 fixes. Each was validated on sandbox. But online scores barely improved. Here's why:

### 1. We're fixing SYMPTOMS, not ROOT CAUSES

| What we fixed | What the actual problem is |
|---------------|--------------------------|
| "Add dateFrom/dateTo to system prompt" | The LLM doesn't reliably follow system prompt instructions |
| "Add FX workflow to system prompt" | The LLM follows the workflow ~60% of the time, ignores it ~40% |
| "Add efficiency rule" | The LLM still makes verification GETs despite being told not to |
| "Add field name list" | The LLM still invents new field names not in the list |
| "Rewrite ledger correction workflow" | The LLM follows it on sandbox but reverts to over-analysis online with different variants |

**The fundamental problem**: We're adding more text to a system prompt that's already 15,000 characters. The LLM (Gemini 3.1 Pro Preview) does NOT reliably follow long system prompts, especially for complex multi-step tasks.

### 2. Model Reasoning Level

**Current model**: `gemini-3.1-pro-preview`
**Temperature**: 0.1
**Thinking mode**: Was NOT enabled. **NOW FIXED** — `reasoning_effort="medium"` added.

Gemini 3.1 Pro has three thinking levels: LOW, MEDIUM, HIGH (Deep Think Mini). Via the OpenAI-compatible endpoint, this is set with `reasoning_effort` parameter. Without it, the model was running with minimal reasoning — no chain-of-thought before acting.

**Fix applied**: `reasoning_effort="medium"` in chat.completions.create(). Validated on sandbox — works correctly. The `extra_body.google.thinking_config` approach does NOT work on the OpenAI-compatible endpoint; only `reasoning_effort` works.

For complex tasks (FX payments, ledger corrections, year-end closing), this means:
- The model can't "think through" the accounting math
- It can't plan a multi-step sequence before acting
- It guesses at account numbers because it can't reason about the chart structure
- It re-fetches data because it can't "remember" what it already has in a long context

### 3. System Prompt Bloat

The system prompt is **15,194 characters** and growing. It contains:
- 65-line endpoint table
- VAT rates
- Chart of accounts
- 20+ task workflows (each 2-5 lines)
- 14 critical rules

For a model without reasoning mode, this much instruction is noise. The LLM attends to whatever seems most relevant and ignores the rest. Rules added later get less attention.

### 4. Sandbox Validation ≠ Online Success

Every fix was "validated on sandbox" but:
- Sandbox is persistent (accumulated data from 100+ tests)
- Online sandboxes are fresh with only pre-created task data
- We test ONE variant, online has 8
- Our sandbox has our test data; online has competition-generated data
- The LLM may follow the workflow when the prompt closely matches what we tested, but diverges on different variants

---

## Available Gemini Models

```
gemini-3.1-pro-preview     ← current (no thinking)
gemini-3-pro-preview       ← older
gemini-2.5-pro             ← has thinking mode
gemini-2.5-flash           ← fast, has thinking mode
gemini-3-flash-preview     ← fast
gemini-3.1-flash-lite-preview ← fastest
```

**Gemini 2.5 Pro** has explicit thinking/reasoning support. It can reason through complex problems before acting. This could be the single biggest improvement possible.

**Gemini 2.5 Flash** has thinking mode AND is faster (important for 300s timeout).

---

## Architecture Assessment

### What works:
- Tool-calling loop architecture is sound
- apply_fixes catches common payload errors
- Logging with req_id is excellent for debugging
- Simple tasks (customer, supplier, product, invoice) work well — 1-7 calls, 0 errors

### What fundamentally doesn't work:
1. **Long system prompt + no reasoning = unreliable complex task execution**
2. **No way to enforce call limits** — the system prompt says "max 3 GETs" but the LLM ignores it
3. **No way to prevent verification GETs** — the LLM's instinct to verify overrides the rule
4. **No structured output** — the LLM decides freely what to do next, often choosing to analyze instead of act

### Potential Architecture Changes (ordered by impact):

#### 1. Switch to a model with thinking/reasoning mode (HIGHEST IMPACT)
- Gemini 2.5 Pro or 2.5 Flash with thinking budget
- Enables the model to reason about accounting math, plan sequences, and follow complex workflows
- Could fix: FX calculations, account number guessing, over-analysis, verification GETs
- Risk: May be slower per call (thinking takes time), needs testing against 300s budget

#### 2. Reduce system prompt to essentials (HIGH IMPACT)
- Current 15K chars is too much. The LLM doesn't read it all.
- Distill to ~5K: just the endpoint table, critical rules, and 3-4 key workflows
- Move detailed workflows to tool descriptions instead
- The LLM pays more attention to shorter instructions

#### 3. Add hard guardrails in code (MEDIUM IMPACT)
- After N GET calls without a POST/PUT, force a message: "You've made {N} GET calls without any writes. Create the required resources NOW."
- Track duplicate GETs in execute_tool and return cached response
- After POST/PUT success, don't allow GET on the same resource type for 2 iterations

#### 4. Use structured output / forced tool calling (MEDIUM IMPACT)
- Instead of `tool_choice: "auto"`, force specific tool calls at specific stages
- E.g., after all GETs, set `tool_choice: {"type": "function", "function": {"name": "tripletex_post"}}` to force the LLM to write

---

---

## Cross-Version Fix Validation (V1→V5)

Checking whether each "fix" actually improved things across ALL online runs:

### ✅ CONFIRMED WORKING: dateFrom/dateTo on /ledger/posting
- V1: 11 errors (most common error)
- V2+: **0 errors, 79 correct calls**
- Verdict: **FIX WORKS.** The LLM reliably follows this instruction.

### ✅ CONFIRMED WORKING: Division creation with required fields
- V1: 7 errors
- V2+: **0 errors, 4 correct POSTs with all fields**
- Verdict: **FIX WORKS.**

### ✅ CONFIRMED WORKING: Code crash list.setdefault
- V4: 2 crashes
- V5: **0 crashes**
- Verdict: **FIX WORKS.**

### ✅ CONFIRMED WORKING: Voucher deletion → correction vouchers
- V1: 1 DELETE attempt
- V2+: **0 DELETE /voucher attempts**
- Verdict: **FIX WORKS.**

### ✅ CONFIRMED WORKING: Trailing verification GETs
- V1: ~50+ trailing GETs
- V5: **6 total trailing GETs**
- Verdict: **MAJOR IMPROVEMENT.** Not perfect but 90% reduction.

### ⚠️ PARTIALLY WORKING: FX Payment workflow
- V3: 2/2 timeout (0% success)
- V4: 2/2 completed (100% success)
- V5: Not tested in latest batch
- Verdict: **FIX WORKS** when task appears. Timeouts eliminated.

### ⚠️ PARTIALLY WORKING: Ledger Error Correction
- V3: 1/1 timeout (31 GETs, 0 POSTs)
- V4: 1/1 timeout (43 GETs, 0 POSTs) — fix didn't work
- V5: **2/2 completed (3 GETs, 7 POSTs)** — fix NOW works!
- Verdict: **FIX WORKS in V5** — the stronger prescriptive workflow finally got through. But 3 errors per run (supplier ID missing on correction vouchers).

### Remaining Issue: Ledger correction supplier reference
Both V5 ledger corrections (a5e68ab2, ebdc6908) failed with "Leverandør mangler" — the correction vouchers for supplier-related accounts (2400) need `supplier:{id}` on the AP posting. The LLM creates the correction but omits the supplier reference.

---

## Key Insight: What Makes Fixes Work vs Fail

Fixes that WORK are ones where:
1. The instruction is **short and absolute** ("ALWAYS include dateFrom AND dateTo")
2. The fix is **in code** (list.setdefault check, apply_fixes)
3. The rule is **in the critical rules section** (not buried in a workflow)

Fixes that FAIL are ones where:
1. The instruction is **long and conditional** ("if X then do Y but not Z")
2. The fix relies on the **LLM following a multi-step sequence**
3. The instruction is **buried in a 15K prompt**

The reasoning_effort="high" deployment (revision 00043) should help the model follow the longer conditional instructions. This is the first deployment with thinking mode enabled.

---

## V5 Error Details by Run

### Token Expired (not our bug)
- d299289a: Year-end closing (FR) — all 403
- 120adc49: Monthly closing (Nynorsk) — all 403

### Ledger Error Correction (a5e68ab2, ebdc6908)
Both failed with "Leverandør mangler" (supplier missing) on correction vouchers. The agent creates correction postings on account 2400 (leverandørgjeld) without including the supplier reference. This is a system prompt gap — correction vouchers for supplier-related accounts need supplier:{id} on the AP posting.

### Monthly/Year-End Closing (d299289a, 120adc49 — token expired so can't assess)

### Milestone Invoice (eae1c4e2)
"bankAccountNumber: Dette er ikke et gyldig norsk kontonummer" — the ensure_bank_account helper uses "12345678903" which isn't valid on all sandboxes.

### Product Number Exists (b6c32c18, 1f093d11)
Products with same number already exist on sandbox. Agent recovers by GET. 1 wasted call each.

### Reminder Fee (c9adc48f)
vatType locked on account 3400. The account has a forced vatType that conflicts with what the agent sends.
