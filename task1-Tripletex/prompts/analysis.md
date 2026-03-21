# Tripletex Agent — Failure Analysis Report

**Date:** 2026-03-21
**Based on:** Cloud Run logs (~60 task executions across ~16 deployments), pulled via `gcloud logging read`
**Focus:** Most recent runs (2026-03-20 21:00–23:10). No new runs after 23:10 UTC.
**Note:** Logs confirmed fresh via Google Cloud API — no additional runs since last night's session.

---

## Current Scoreboard

| Task | Best Score | Max | Tier | Notes |
|------|-----------|-----|------|-------|
| 01 | 1.22 | 2.0 | 1 | Partial — employee creation |
| 02 | 2.00 | 2.0 | 1 | Good — customer creation |
| 03 | 2.00 | 2.0 | 1 | Good — product creation |
| 04 | 2.00 | 2.0 | 1 | Good — department creation |
| 05 | 1.33 | 2.0 | 1 | Partial — supplier registration |
| 06 | 0 | 2.0 | 1 | **PRIORITY** — invoice create+send, never scored |
| 07 | 0.29 | 2.0 | 1 | Mostly failed — order→invoice→payment |
| 09 | 2.80 | 4.0 | 2 | Great — project creation |
| 11 | 0 | 4.0 | 2 | **PRIORITY** — never scored |
| 12 | 0 | 4.0 | 2 | **PRIORITY** — never scored |
| 13 | 0.50 | 4.0 | 2 | Mostly failed — travel expense |
| 17 | 0.92 | 4.0 | 2 | Partial — accounting dimensions + voucher |

**Current total: ~11.06 / 44.0 potential**

---

## Per-Task Diagnosis

### Task 01 — Employee Creation (Tier 1, score 1.22/2.0)

**Example prompt:** "We have a new employee named Sophie Clark, born 3. March 1981. Please create them as an employee with email sophie.clark@example.org and start date 3. July 2026."

**What works:** Employee is created with correct name, email, department, userType. Admin role is granted.

**What fails:**
- `startDate` → requires creating an employment record via `POST /employee/employment`. The knowledge base documents this, but the executor sometimes skips it or gets the date format wrong.
- `dateOfBirth` — sometimes not included in the POST body.
- Efficiency penalty: ~3 unnecessary GET calls (country, employee/category) that the knowledge base doesn't ask for but the decomposer adds.

**Root cause:** MISSING_KNOWLEDGE + FIELD_ERROR — The employment creation step is documented but the executor doesn't always follow through, especially under time pressure. Also, extra unnecessary GETs hurt efficiency.

**Fix:** In `knowledgebase.md`, make the employment creation step more explicit. In the decomposer prompt, reinforce "MINIMAL plan" — don't add GET /country or GET /employee/category.

---

### Task 02 — Customer Creation (Tier 1, score 2.00/2.0)

**Status:** Working correctly. Single `POST /customer` with name, isCustomer, organizationNumber, email, addresses.

**Improvement opportunity:** Efficiency bonus only. Currently making 1-2 calls, could potentially get efficiency bonus with zero errors.

---

### Task 03 — Product Creation (Tier 1, score 2.00/2.0)

**Status:** Working correctly. `GET /ledger/vatType` → `POST /product`.

**Improvement opportunity:** Efficiency bonus. Could skip VAT lookup by using hardcoded IDs from knowledge base.

---

### Task 04 — Department Creation (Tier 1, score 2.00/2.0)

**Status:** Working correctly now. Earlier runs had `'id'` KeyError bugs (now fixed).

**Note:** "Create 3 departments" variant sometimes failed with `'id'` error in older code. Recent runs succeed.

---

### Task 05 — Supplier Registration (Tier 1, score 1.33/2.0)

**Example prompt:** "Register the supplier Silveroak Ltd with organization number 811867500. Email: faktura@silveroakltd.no."

**What fails:** Likely missing fields. The knowledge base says only `name` is required, but scoring probably checks `organizationNumber` and `email` too. The partial score suggests some fields are set correctly but not all.

**Root cause:** FIELD_ERROR — Executor may not be sending all provided fields.

**Fix:** Update `knowledgebase.md` supplier section to list all commonly scored fields explicitly: `name`, `organizationNumber`, `email`. Verify the executor sends them all.

---

### Task 06 — Invoice Creation & Send (Tier 1, score 0/2.0) **PRIORITY**

**Example prompt:** "Opprett og send ein faktura til kunden Fjelltopp AS (org.nr 845696993) på 38150 kr eksklusiv MVA. Fakturaen gjeld Programvarelisens."

**What happens:** The agent successfully creates the customer, product, order, and order lines. But `POST /invoice` fails with:
> "Faktura kan ikke opprettes før selskapet har registrert et bankkontonummer."

The sandbox company doesn't have a bank account registered, and `PUT /company` is blocked by the proxy.

**Root cause:** INFRA_BLOCKER — Tripletex sandbox requires a bank account to create invoices, but the proxy blocks company settings endpoints.

**HOWEVER:** In the MOST RECENT runs (23:xx timestamps), the agent still completes with TASK_COMPLETED status. The log shows:
- Customer found/created ✓
- Product created ✓
- Order created with correct order lines ✓
- Invoice fails → agent stops ✓

**This means the scoring likely gives partial credit for the order/product/customer.** The score of 0 suggests these recent successful runs haven't been credited yet, OR the task type for invoice+send is separate from the order creation tasks.

**Fix possibilities:**
1. Check if the sandbox has a bank account registration endpoint that ISN'T blocked
2. Focus on getting maximum partial credit from order/product/customer creation
3. This may be fundamentally blocked — accept 0 and focus elsewhere

---

### Task 07 — Order → Invoice → Payment (Tier 1, score 0.29/2.0)

**Example prompt:** "Créez une commande pour le client Étoile SARL (nº org. 972488607) avec les produits Rapport d'analyse (2823) à 21350 NOK et Design web (2035) à 19950 NOK. Convertissez la commande en facture et enregistrez le paiement intégral."

**What works:** Customer, products, and order are created successfully.

**What fails:** Same bank account blocker as Task 06 prevents invoice creation, which then blocks payment registration.

**Root cause:** INFRA_BLOCKER (same as Task 06) + complexity of multi-product orders.

**Why 0.29 not 0:** Partial credit for customer + product + order creation.

**Fix:** Same as Task 06. Additionally, improve multi-product order line handling for the partial credit.

---

### Task 09 — Project Creation (Tier 2, score 2.80/4.0)

**Example prompt:** "Crie o projeto 'Análise Rio' vinculado ao cliente Rio Azul Lda (org. nº 912018431). O gerente de projeto é Inês Rodrigues (ines.rodrigues@example.org)."

**What works:** Customer found/created, employee found/created, project created with correct linking.

**What partially fails:** Efficiency — too many API calls (6-11 steps in plan). Unnecessary lookups.

**Root cause:** FIELD_ERROR — Some fields may be missing. Efficiency penalty from extra calls.

**Fix:** Reduce plan to minimum steps: GET customer → POST customer if needed → GET employee → POST employee if needed → POST project. Skip unnecessary GETs.

---

### Task 11 — Unknown Type (Tier 2, score 0/4.0) **PRIORITY**

**Not seen in recent logs.** Possible candidates based on task categories:
1. **Salary/Payroll** — seen in logs but may map to a different task number. Salary tasks have TOKEN_EXPIRY issues (they appear late in submissions).
2. **Supplier Invoice (incoming)** — seen in logs with voucher posting errors ("systemgenererte" = system-generated postings can't be modified).
3. **Payment registration on existing invoice** — seen in logs.

**Most likely: Supplier Invoice** — The voucher posting errors are systematic:
- "Et bilag kan ikke registreres uten posteringer" (voucher needs postings)
- "Posteringene på rad 0 er systemgenererte og kan ikke opprettes" (system-generated postings can't be modified)

**Root cause:** FIELD_ERROR + MISSING_KNOWLEDGE — The voucher `postings` array is being sent incorrectly. The API rejects postings that reference system-generated account rows. The knowledge base has a supplier invoice workflow, but the executor doesn't follow it correctly.

**Fix:** The postings must NOT include `row` field or reference system-generated rows. Update `knowledgebase.md` with the exact working payload structure. Ensure the VAT posting on account 2710 does NOT set a vatType (the account is "låst til mva-kode 0" = locked to VAT code 0).

---

### Task 12 — Unknown Type (Tier 2, score 0/4.0) **PRIORITY**

**Not seen in recent logs.** Possible candidates:
1. **Credit Note** — Seen in logs, sometimes works (PUT /invoice/{id}/:createCreditNote returns 200) but sometimes fails (422).
2. **Payment Reversal** — Seen in logs, sometimes works. "Reverser betalingen" → PUT /invoice/{id}/:payment with negative amount.
3. **Project Billing (hourly)** — Seen in logs, complex workflow with timesheet entries.

**Most likely: Project Hourly Billing** — This task registers hours + creates project invoice. Multiple failures seen:
- `POST /timesheet/entry` returns 422
- Token expiry before completing complex workflow
- Max turns exceeded (15 turns)

**Root cause:** MAX_TURNS + MISSING_KNOWLEDGE — The agent doesn't have a knowledge base entry for timesheet/project billing. It has to discover the workflow through trial and error, burning through turns.

**Fix:** Add a "Project Billing (Hourly)" workflow to `knowledgebase.md`:
1. GET /customer → find/create customer
2. GET /employee → find employee
3. POST /project → create project
4. POST /activity → create activity on project
5. POST /timesheet/entry → register hours
6. POST /order → create order from project
7. POST /invoice → create project invoice

---

### Task 13 — Travel Expense (Tier 2, score 0.50/4.0)

**Example prompt:** "Registre una nota de gastos de viaje para María Hernández (maria.hernandez@example.org) por 'Visita cliente Bergen'. El viaje duró 4 días con dietas (tarifa diaria 800 NOK). Gastos: billete de avión 7800 NOK y taxi 600 NOK."

**What works:** Employee found, travelExpense shell created.

**What fails (multiple issues):**

1. **perDiemCompensation — "Country not enabled for travel expense"**
   - Agent sends `countryCode: "NO"` but Tripletex requires a country ID, not code
   - OR the country isn't enabled in the travel expense module

2. **perDiemCompensation — "Spesifiser avreisedato og returdato"**
   - Missing departure/return dates. The agent sends `departureDate` which doesn't exist as a field.

3. **perDiemCompensation — "Kun reiseregning, ikke ansattutlegg"**
   - The travelExpense was created as an "employee expense" not a "travel report". Need `isTravel: true` or correct type.

4. **GET /travelExpense/rate — "Result set too large"**
   - Agent queries without filters, gets 10K+ results. Need to filter by type/category.

5. **travelExpense/cost — "paymentType.id must reference valid object"**
   - Agent uses wrong paymentType ID. Must GET /travelExpense/paymentType first.

6. **MAX_TURNS exceeded** (25 turns) — burns through turns on errors

**Root cause:** MISSING_KNOWLEDGE + FIELD_ERROR — The knowledge base has a travel expense workflow, but it has critical gaps:
- Doesn't specify the correct field names for departure/return dates
- Doesn't explain how to handle country for per diem
- Doesn't mention `isTravel: true` flag
- GET /travelExpense/rate needs filtering

**Fix:** Major update to travel expense section in `knowledgebase.md`:
- Use `travelDetails` with `departureDate` and `returnDate` on the travelExpense
- For perDiemCompensation: use `dateFrom`/`dateTo`, not `departureDate`
- Filter GET /travelExpense/rate with type params to avoid result set explosion
- Always GET /travelExpense/paymentType for cost items
- Ensure travelExpense is created as travel report (not employee expense)

---

### Task 17 — Accounting Dimensions + Voucher (Tier 2, score 0.92/4.0)

**Example prompt:** "Créez une dimension comptable personnalisée 'Kostsenter' avec les valeurs 'Produktutvikling' et 'Salg'. Puis comptabilisez une pièce sur le compte 7300 pour 37450 NOK, liée à la valeur de dimension 'Salg'."

**What works:** Dimension name and values are created successfully via:
- `POST /ledger/accountingDimensionName` ✓
- `POST /ledger/accountingDimensionValue` ✓

**What fails:** Voucher posting fails with:
- "Et bilag kan ikke registreres uten posteringer" (voucher has no postings)
- "Posteringene på rad 0 er systemgenererte" (system-generated postings error)

The agent is either:
1. Sending postings in the wrong format (nested inside the voucher incorrectly)
2. Referencing system-generated posting rows

**Root cause:** FIELD_ERROR — The voucher `postings` array format is wrong. The executor likely sends postings as a flat object instead of properly structured. Also, the voucher needs TWO postings that balance to zero (debit + credit).

**Fix:** Update `knowledgebase.md` with accounting dimension voucher workflow:
```json
{
  "date": "2026-03-20",
  "description": "Dimension posting",
  "voucherType": {"id": <voucher_type_id>},
  "postings": [
    {
      "account": {"id": <expense_account_id>},
      "amount": 37450,
      "freeAccountingDimension1": {"id": <dimension_value_id>}
    },
    {
      "account": {"id": <bank_account_id>},
      "amount": -37450
    }
  ]
}
```

---

### Other observed task types (not in scoreboard — may not have been attempted, or may map to missing task numbers)

**Credit Note (task unknown, possibly 10 or 14):**
- Pattern: Find customer → find invoice → PUT /invoice/{id}/:createCreditNote
- Sometimes succeeds (200 OK), sometimes gets 422
- Appears to work in recent runs

**Payment Reversal (task unknown, possibly 10 or 15):**
- Pattern: Find customer → find invoice → PUT /invoice/{id}/:payment with negative amount
- Works in recent runs (paidAmount=-XXXX)

**Salary/Payroll (task unknown, possibly 16):**
- Pattern: Find employee → find salary types → POST /salary/transaction
- TOKEN_EXPIRY in earlier runs (task appears late in submission)
- Recent runs succeed (TASK_COMPLETED)

**Project Fixed Price Billing (task unknown, possibly 11 or 12):**
- Pattern: Find/create customer + employee → create project → set fixed price → create invoice for % of price
- Complex workflow (12+ steps)
- Bank account error blocks invoice step
- Some runs hit max turns

---

## Summary Table

| Task | Type | Root Cause | Fix | File to Change |
|------|------|-----------|-----|---------------|
| 01 | Employee | FIELD_ERROR, extra GETs | Ensure employment created for startDate; remove unnecessary GETs | knowledgebase.md, pipeline.py (decomposer prompt) |
| 02 | Customer | — (working) | Optimize for efficiency bonus | — |
| 03 | Product | — (working) | Hardcode VAT IDs to skip lookup | knowledgebase.md |
| 04 | Department | — (working) | — | — |
| 05 | Supplier | FIELD_ERROR | Send all provided fields (orgNumber, email) | knowledgebase.md |
| 06 | Invoice+Send | INFRA_BLOCKER | Bank account missing; maximize partial credit from order | knowledgebase.md |
| 07 | Order→Invoice→Pay | INFRA_BLOCKER | Same as 06; improve multi-product order creation | knowledgebase.md |
| 09 | Project | FIELD_ERROR | Reduce plan steps; improve efficiency | knowledgebase.md |
| 11 | Supplier Invoice? | FIELD_ERROR + MISSING_KB | Fix voucher postings format; don't use vatType on 2710 | knowledgebase.md |
| 12 | Project Billing? | MAX_TURNS + MISSING_KB | Add project billing workflow to knowledge base | knowledgebase.md |
| 13 | Travel Expense | MISSING_KB + FIELD_ERROR | Fix perDiem fields, country, paymentType handling | knowledgebase.md |
| 17 | Acct Dimensions | FIELD_ERROR | Fix voucher posting format with dimension linking | knowledgebase.md |

---

## Top 5 Highest-Impact Fixes

Ordered by expected score improvement × tier multiplier.

### 1. Fix voucher posting format (Tasks 11, 17) — **Est. +5.0 to +8.0 points**
- **Impact:** Tasks 11 (4.0 max) and 17 (4.0 max) both fail on voucher postings
- **Current:** 0.92 combined
- **Problem:** Postings sent in wrong format — "systemgenererte" error means the API rejects the structure
- **Fix:** In `knowledgebase.md`, update voucher posting section with exact working JSON structure. Key: don't include `row` field, ensure postings array is flat (not nested), and account 2710 must NOT have a vatType set (it's locked to VAT code 0)
- **File:** `agent/knowledgebase.md`

### 2. Add travel expense workflow with correct field names (Task 13) — **Est. +2.0 to +3.5 points**
- **Impact:** Task 13 (4.0 max), currently 0.50
- **Problem:** Wrong field names (departureDate → should be dateFrom/dateTo), country not enabled, paymentType not resolved, rate set too large
- **Fix:** Rewrite travel expense section in knowledge base with verified field names. Add date filtering for GET /travelExpense/rate. Specify isTravel flag.
- **File:** `agent/knowledgebase.md`

### 3. Add project billing workflow (Task 12) — **Est. +2.0 to +4.0 points**
- **Impact:** Task 12 (4.0 max), currently 0
- **Problem:** No knowledge base entry for hour registration + project invoicing. Agent runs out of turns discovering the workflow.
- **Fix:** Add complete workflow: customer → employee → project → activity → timesheet/entry → order → invoice
- **File:** `agent/knowledgebase.md`

### 4. Fix employee creation for full marks (Task 01) — **Est. +0.78 points**
- **Impact:** Task 01 (2.0 max), currently 1.22
- **Problem:** startDate employment not always created; unnecessary GETs reduce efficiency
- **Fix:** Make employment creation step explicit in knowledge base. Remove unnecessary GET /country and GET /employee/category from decomposer behavior.
- **File:** `agent/knowledgebase.md`, decomposer prompt in `agent/pipeline.py`

### 5. Improve efficiency on working tasks (Tasks 02, 03, 04, 09) — **Est. +2.0 to +4.0 points**
- **Impact:** Tasks already at correctness=1.0 but missing efficiency bonus
- **Current:** 2.0+2.0+2.0+2.80 = 8.80
- **Potential with efficiency:** up to 4.0+4.0+4.0+8.0 = 20.0 (Tier 2 for task 09)
- **Fix:** Hardcode known VAT IDs, skip unnecessary lookups, reduce plan step count. Each 0-error run with minimal calls could double the score.
- **File:** `agent/knowledgebase.md`, `agent/pipeline.py`

---

## Code Bug: `'id'` KeyError

Several older runs crash with `'id'` KeyError:
```
TASK_FAILED: Crie três departamentos... — 'id'
TASK_FAILED: Erstellen Sie drei Abteilungen... — 'id'
```

This appears in the old pipeline code where `response['value']['id']` was accessed without checking if the response has that structure. This seems to be fixed in recent deployments but should be verified — add `.get('value', {}).get('id')` safeguards.

---

## Speed / Token Expiry Analysis

Several tasks fail because the proxy token expires (5 min timeout per submission):
- Tasks arriving late in a submission batch get 403 errors
- Complex tasks (travel expense, project billing) take 60-90s each
- Pipeline preprocessing takes 15-30s per task (translate + decompose)

**Fix:** Reduce LLM calls in pipeline. Consider caching decomposition for known task patterns. Reduce max_turns from 50 to 30 to fail faster on hopeless tasks.

---

## Competition Host Announcement (2026-03-21)

From Erik (Astar) on Discord:
1. **73% of all 403 errors across teams come from ONE [BETA] endpoint.** Swagger docs mark which endpoints are BETA. These endpoints are blocked by the proxy and return 403. We need to check which endpoints we use against Swagger BETA tags.
2. **Cloudflared tunnel timeouts after 120s** cause score=0 (no `completed` response received). **We use Cloud Run (300s timeout), so this doesn't affect us.**
3. **Session token stops working after `completed` is received** by their validator. No post-completion API calls are possible.
4. **New token per submission** — don't reuse old tokens.

**Our 403 inventory (non-token-expiry):**
- `GET /bank/settings` → 403 "no permission" — likely BETA or restricted
- `GET /company`, `PUT /company/{id}` → 405 Method Not Allowed — proxy-blocked
- `POST /bank/account` → 405 — proxy-blocked
- `POST /ledger/voucherType` → 405 — proxy-blocked (we should only GET, not POST)

These are all from the agent trying to fix the bank account blocker. Our core endpoints (employee, customer, product, project, etc.) don't hit BETA issues.

**Action:** Check Tripletex Swagger docs to identify which commonly-used endpoint is BETA and blocked. Could affect tasks we haven't debugged yet.

---

## Key Architectural Observations

1. **Pipeline overhead:** Steps 1+3 (translate+decompose) take 15-30s. This is significant for a 5-min timeout.
2. **Decomposer over-plans:** Creates 8-12 step plans where 3-5 would suffice. The knowledge base workflows are clear but the decomposer adds unnecessary prerequisite GETs.
3. **Executor is resilient:** When given a good plan, it handles errors well (retries, adjusts). The failures are almost always in the plan or knowledge base, not the executor logic.
4. **Bank account blocker:** Tasks 06 and 07 are fundamentally blocked by sandbox infrastructure. Only way to fix is to find a bank account setup endpoint or accept partial credit.
