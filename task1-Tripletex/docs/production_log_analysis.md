# Production Log Analysis

---

# V4 ANALYSIS — Revision 00041 (FX workflow + efficiency rule)

**Deployment time**: ~18:50 UTC (2026-03-21)
**Total runs**: 36 (4 still running/timed out at log fetch time)
**Changes in this deploy**: FX payment workflow added, stronger efficiency rule #10

## V4 Summary

| Outcome | Count | Req IDs |
|---------|-------|---------|
| ✅ Clean (0 errors) | 18 | 02429449, 6c193d05, 55b7083b, 7ae16a0c, 5fcc4052, a5922aa1, 4b4e3d28, 09e3faa4, e74f2ebb, 349b6e77, eecd67bb, 3eb0feb1, ad5dcccd, f6649e02, 02e6e2e9, 0fc920c4, 12716714, 0fee50b5 |
| ✅ Clean but high calls | 4 | 98757578(40), 66801567(19), 3eb0feb1(22), 75980176(10) |
| ⚠️ Completed with errors | 5 | cbc48484(2err), c59e441f(1err), 14d31697(1err), 509de7b8(3err), ac356249(6err) |
| ❌ Token expired (403) | 5 | 40dea551, 538ea526, 51869a98, 1f153268, 58ebb784 |
| 💥 Code crash | 1 | 371e12e4 |
| 🔄 Still running/timeout | 3 | 4cae6184, 1decab66, 21dfab69 |

## V4 Detailed Run Analysis

### ✅ Clean runs (0 errors)

**02429449** — Create Customer (NO). 1 call, 11s. Perfect.
**5fcc4052** — Create Customer (ES). 1 call, 10s. Perfect.
**09e3faa4** — Create Departments (EN). 2 calls, 14s. **NOTE: task asked for 3 departments, only 2 calls — likely used batch? Or created 1 and something went wrong.** Needs investigation.
**eecd67bb** — Create Project (ES). 3 calls, 16s. Clean.
**f6649e02** — Create Project (FR). 3 calls, 15s. Clean.
**02e6e2e9** — Create Employee (FR). 3 calls, 21s. Clean.
**12716714** — Payment on Invoice (EN). 5 calls, 23s. Clean.
**4b4e3d28** — Payment Reversal (PT). 4 calls, 21s. Clean.
**6c193d05** — Fixed-Price Project (PT). 7 calls, 31s. Clean.
**7ae16a0c** — Order→Invoice (ES). 8 calls, 33s. Clean.
**55b7083b** — Employee from PDF (Nynorsk). 8 calls, 46s. Clean.
**ad5dcccd** — Employee from PDF (NO). 6 calls, 38s. Clean.
**0fc920c4** — Supplier Invoice from PDF (ES). 7 calls, 40s. Clean.
**0fee50b5** — Supplier Invoice (DE). 6 calls, 30s. Clean.

### ✅ Clean but high call count (efficiency concern)

**98757578** — Monthly Closing (EN). **40 calls**, 118s. 0 errors but 39 GETs vs 1 POST. Massive over-reading of ledger data.
**3eb0feb1** — Monthly Closing (PT). **22 calls**, 88s. 0 errors. Same pattern — too many GETs analyzing balance sheet.
**75980176** — Receipt Voucher (NO). 10 calls, 41s. 9 GETs to look up accounts one by one.
**349b6e77** — Cost Analysis + Projects (Nynorsk). 20 calls, 71s. Created 3 projects + 3 activities — 12 POSTs needed but 8 GETs extra.

### ⚠️ Completed with errors

**c59e441f** — FX Payment (DE). 16 calls, 1 error, 127s. Error: `dateFrom >= dateTo` on voucher query. **FX workflow partially worked** — registered payment and posted exchange rate voucher despite the error.

**a5922aa1** — FX Payment (EN). 12 calls, 0 errors, 86s. **FX workflow working well.** 9 GETs + 1 POST + 1 PUT. Improvement over v3 (was timing out).

**14d31697** — Employee from PDF (DE). 6 calls, 1 error, 34s. Error: `email: Må angis for Tripletex-brukere` — employee created without email (PDF extraction missed it). Recovered.

**509de7b8** — Salary (ES). 15 calls, 3 errors, 64s. Errors: salary failed (no employment), employment creation failed (no dateOfBirth), second salary attempt also failed. **Salary pipeline partially broken** — the `create_employment` helper didn't set dateOfBirth first.

**cbc48484** — Accounting Dimensions (EN). 9 calls, 2 errors, 39s. Error: `accountingDimensionName: Feltet eksisterer ikke` on dimension value creation — LLM used wrong field name. Likely recovered by retrying.

**ac356249** — Bank Reconciliation (Nynorsk). 36 calls, 6 errors, 139s. Errors: supplierInvoice missing dates, invalid invoice numbers on payment. **Partially completed** — matched some payments but wrong invoice IDs for others.

### ❌ Token expired (403 on all calls)

**40dea551, 538ea526, 51869a98, 1f153268, 58ebb784** — All 5 show `"Invalid or expired proxy token"` on every API call. These are NOT our bug — the competition proxy invalidated the token (likely because the validator already received our response, or concurrent task on same sandbox finished first). **5 of 36 runs (14%) lost to token expiry.**

### 💥 Code crash

**371e12e4** — Full Project Lifecycle (PT). Crashed with `'list' object has no attribute 'setdefault'`. This is a **BUG in apply_fixes.py** — likely the salary transaction fix tries to call `.setdefault()` on a list instead of a dict when the payload structure is unexpected.

### 🔄 Still running / likely timed out

**4cae6184** — Ledger Error Correction (PT). 41+ GETs, 0 POSTs visible. Same pattern as v3 — over-analyzing, never creating corrections.
**1decab66** — Monthly Closing (DE). 14+ GETs, 0 POSTs. Still analyzing.
**21dfab69** — Full Project Lifecycle (NO). 17 tools visible. May have completed or timed out.

## V4 Error Categorization

| Error Type | Count | Runs | Status |
|------------|-------|------|--------|
| Token expired (proxy 403) | 5 runs (all calls) | 40dea551, 538ea526, 51869a98, 1f153268, 58ebb784 | NOT OUR BUG — competition infrastructure |
| Code crash: list.setdefault | 1 run | 371e12e4 | **NEW BUG in apply_fixes.py** |
| Salary: no employment/dateOfBirth | 3 errors in 1 run | 509de7b8 | Known — dateOfBirth not set before employment |
| Accounting dimension wrong field | 2 errors in 1 run | cbc48484 | Known — field name invention |
| Bank recon: wrong invoice IDs | 2 errors in 1 run | ac356249 | Known — matching logic issues |
| FX: dateFrom >= dateTo | 1 error in 1 run | c59e441f | Minor — query range same start/end date |
| Employee: missing email from PDF | 1 error in 1 run | 14d31697 | PDF extraction quality |
| Ledger error correction: all GETs no POSTs | 1+ runs | 4cae6184 | Known — still over-analyzing |
| Monthly closing: excessive GETs | 2+ runs | 98757578(40 calls), 3eb0feb1(22) | **NEW — efficiency problem** |

## V4 Key Findings

### POSITIVE — What improved:
1. **FX Payment works!** c59e441f (16 calls) and a5922aa1 (12 calls) both completed FX tasks with agio voucher. v3 had 100% timeout on FX. Now 0% timeout.
2. **Employee from PDF** — 3 runs (55b7083b, ad5dcccd, 14d31697), all completed. Good extraction.
3. **Supplier Invoice from PDF** — 0fc920c4 completed cleanly. 7 calls, 40s.
4. **Simple tasks extremely efficient** — customer(1 call), departments(2), project(3), employee(3).
5. **No LLM thinking loop timeouts** in the non-token-expired runs — the 270s budget + FX workflow prevented the stuck-thinking issue.

### NEGATIVE — What still fails:
1. **Token expiry** — 14% of runs lost. Not our bug but hurts score. The Slack announcement mentioned "session token will stop working after our validator has received the response" — this means if 3 concurrent tasks run on same sandbox, the first to complete invalidates the token for the other 2.
2. **Code crash** — `'list' object has no attribute 'setdefault'` in apply_fixes.py. Must fix.
3. **Monthly closing excessive calls** — 40 calls for a task that should take ~5-8. The LLM reads entire balance sheet and all postings repeatedly.
4. **Ledger error correction still all GETs** — 4cae6184 making 41+ GET calls with 0 POSTs. The rewritten workflow in system prompt didn't prevent over-analysis.
5. **Salary dateOfBirth** — the `create_employment` helper doesn't ensure dateOfBirth is set on the employee first.
6. **Efficiency across the board** — many "0 error" runs still have 2-3x optimal call count due to extra GET calls.

### ~~NEW BUG: apply_fixes.py crash~~ → 🟢 FIXED
**`371e12e4`**: `'list' object has no attribute 'setdefault'`
**Fixed**: Added `isinstance(payload, dict)` check in agent.py before calling apply_fixes. List payloads (batch endpoints like POST /order/orderline/list) now pass through without crashing.

---

# V2 ANALYSIS — Post-fix deployment (revision 00039)

**Deployment time**: ~16:50 UTC (2026-03-21)
**Total runs analyzed**: 9
**Source**: Cloud Run logs for `tripletex-agent` in `europe-north1`
**Result**: 0 tasks improved. Fixes validated on sandbox did NOT translate to online improvements.

## V2 Run-by-Run Analysis

### V2 Run 1 — Payment on invoice
- **Calls**: 12, **Errors**: 0, **Time**: 50s
- Registered payment on invoice. Clean execution.
- **Status**: Likely working — but score depends on whether correct invoice was found and correct amount paid.

### V2 Run 2 — Invoice payment + reminder/send (interleaved logs)
- **Calls**: 12, **Errors**: 0, **Time**: 50s
- Logs are interleaved with Runs 1 and 3 (3 concurrent sandboxes). Visible tool calls include: invoice payment (paidAmount=5000), reminder product creation ("Taxa de lembrete"), invoice send, voucher for supplier cost, project creation with activities.
- **Note**: Cloud Run logs don't separate by request when concurrent — tool calls from all 3 runs appear mixed. Accurate per-run attribution is not possible from these logs.

### V2 Run 3 — Complex multi-task (the big one)
- **Calls**: 10 final (28 tool calls visible), **Errors**: 4, **Time**: 41s
- **STILL FAILING errors**:
  - `POST /supplier → bankAccount: Feltet eksisterer ikke` — LLM invented `bankAccount` field on supplier
  - `POST /employee/employment → employmentType: Feltet eksisterer ikke` — wrong field placement (should be in employmentDetails)
  - `POST /ledger/voucher → dueDate: Feltet eksisterer ikke` — same dueDate issue from v1 (rule #14 told it to remove and retry — it DID retry successfully)
  - `PUT /employee/employment/details → standardWorkingHours: Feltet eksisterer ikke` — same invented field from v1
- **POSITIVE**: Division creation worked first try (used organizationNumber+municipality+municipalityDate correctly!)
- **FAILED_ONLINE**: `employmentType` at root level, `bankAccount` on supplier, `standardWorkingHours` on employment details

### V2 Run 4 — Employment details continuation
- **Calls**: 9, **Errors**: 2 (carried from run 3), **Time**: 62s
- Tried `shiftDurationHours` on employment details — another invented field

### V2 Run 5 — Interleaved with Run 4 (concurrent)
- **Calls**: 11, **Errors**: 2, **Time**: 67s
- Logs interleaved with Run 4. Tool calls not attributable to a specific run.

### V2 Run 6 — Voucher/bookkeeping task
- **Calls**: 9, **Errors**: 0, **Time**: 48s
- Created voucher for "Skrivebordlampe Clas Ohlson". Clean execution.
- **Status**: Looks correct.

### V2 Run 7 — Year-end closing / depreciation (Tier 3)
- **Calls**: 26, **Errors**: 0, **Time**: 95s
- Created depreciation vouchers for Kontormaskiner, Kjøretøy, IT-utstyr, prepaid rent reversal.
- **POSITIVE**: Used dateFrom/dateTo correctly on all GET /ledger/posting and /balanceSheet calls! Fix 1 works.
- **POSITIVE**: No timeout (was 100s timeout bug before, now 270s budget).
- **Status**: Completed but score depends on whether amounts/accounts are correct.

### V2 Run 8 — Year-end closing continuation + milestone invoice (multi-task)
- **Calls**: 10, **Errors**: 0, **Time**: 61s
- More depreciation vouchers + milestone invoice for French project "Développement e-commerce".
- **NEGATIVE**: `PUT /project/{id}` to set isFixedPrice — this is a BETA endpoint! Likely returned 403 silently or the response was ignored.
- **Status**: Partial — depreciation might work, but project update probably failed.

### V2 Run 9 — Account creation + tax provision (Tier 3 continuation)
- **Calls**: 38, **Errors**: 2, **Time**: 196s
- Tried to create account 8700 (Skattekostnad) with wrong `type` values.
- `TAXES_AND_EXTRAORDINARY_ITEMS` → rejected, `OTHER_EXPENSES` → rejected, `OPERATING_EXPENSES` → worked.
- **POSITIVE**: Eventually figured out the right type. Used 196s (would have timed out at 100s in v1!)
- **Status**: Completed but wasted 2 calls guessing account type.

## V2 Error Summary

| Error | Count | Same as v1? | Fix status |
|-------|-------|-------------|------------|
| Invented field: `bankAccount` on supplier | 1 | NEW | Not covered by rule #14 (new field) |
| Invented field: `employmentType` on employment root | 1 | Similar to v1 `employmentForm` | Rule #14 exists but LLM still guesses |
| Invented field: `dueDate` on voucher | 1 | YES same | Rule #14 works — LLM retried successfully |
| Invented field: `standardWorkingHours` on details | 1 | YES same | Rule #14 exists but LLM still tries it |
| Invented field: `shiftDurationHours` on details | 1 | NEW | Not in rule #14 |
| Wrong `type` enum on POST /ledger/account | 2 | NEW | Not covered |
| BETA: `PUT /project/{id}` | 1 | Known BETA | Not addressed yet |

## V2 Key Observations

### What IMPROVED:
1. **dateFrom/dateTo on ledger/posting** — Fix 1 works! All GET /ledger/posting calls include dates. 0 date-related errors (was 11 in v1).
2. **Division creation** — Fix 4 works! Agent used correct fields (organizationNumber, municipality, municipalityDate) on first attempt.
3. **No timeouts** — 270s budget means complex tasks complete. Run 9 used 196s which would have failed at 100s.
4. **Voucher dueDate recovery** — Rule #14 partially works. LLM tries dueDate but removes it and retries.

### What STILL FAILS:
1. **LLM still invents field names** — Rule #14 tells it to remove and retry, but the LLM still tries plausible fields before getting the error. New fields appear that weren't in the rule's list (bankAccount, shiftDurationHours).
2. **Employment details fields** — The LLM consistently guesses wrong field names for employment details (workingHoursPerWeek, standardWorkingHours, shiftDurationHours). It doesn't know the actual fields.
3. **PUT /project/{id} is BETA** — We haven't addressed this. The milestone invoice task needs to update project with isFixedPrice but can't.
4. **POST /ledger/account type enum** — The LLM doesn't know valid values for the `type` field on accounts. Wastes 2 calls guessing.
5. **Score is field-by-field** — Even when the agent "completes" a task, if field values are wrong (e.g. wrong depreciation amounts, wrong account numbers), the score is 0. The agent may be doing the right workflow but with wrong data.

---

# V3 ANALYSIS — Post-logging deployment (revision 00040)

**Deployment time**: ~17:14 UTC (2026-03-21)
**Total runs analyzed**: 13 (with request IDs — fully traceable)
**Logging**: Each line tagged with `[req_id]` + prompt preview at start.

## V3 Run-by-Run Analysis

### cc305219 — ✅ Create+Send Invoice (Nynorsk)
- **Task**: "Opprett og send ein faktura til kunden Fjelltopp AS (14900 kr, Opplæring)"
- **Result**: 11 calls, 0 errors, 62s. Clean.

### 4f488011 — ✅ Salary (Nynorsk)
- **Task**: "Køyr løn for Gunnhild Aasen, grunnløn 51800 kr + bonus 5700 kr"
- **Result**: 8 calls, 0 errors, 55s
- **POSITIVE**: Created division with correct fields first try! Division fix works online.
- **POSITIVE**: Set dateOfBirth on employee before employment. Salary fix works.

### cfc70ffc — ⏰ TIMEOUT 507s — Employee from PDF (Portuguese, Tier 3)
- **Task**: "Voce recebeu um contrato de trabalho (ver PDF anexo). Crie o funcionario..."
- **Result**: 9 calls, 2 errors, 507s timeout
- **What happened**: Created employee Bruno Pereira, created division, created employment. Then got stuck trying to set `employmentType: "ORDINARY"` on employment (doesn't exist at root level) and `occupationCode` on employment details. Spent 500+s on LLM calls that produced no further API calls.
- **Issue**: LLM gets stuck in a loop thinking about what to do next without making API calls. The 270s time_budget in our code doesn't apply because the LLM call itself takes the time (each Gemini call can be 10-30s).
- **NEW ISSUE**: `time_budget` only checks elapsed time BETWEEN LLM calls, not during. A single slow LLM call can exceed the budget.

### db25f6e3 — ✅ Employee from PDF (Portuguese, Tier 3)
- **Task**: Same type as cfc70ffc but different data variant
- **Result**: 12 calls, 2 errors, 90s
- **Errors**: `employmentType` at root (wrong field placement), then `remunerationType: "FIXED_SALARY"` → retried with `"MONTHLY_WAGE"` which worked.
- **POSITIVE**: Completed within time. PDF extraction worked. Employee + employment + details created.

### ac00b88a — ✅ Bank Reconciliation from CSV (Nynorsk, Tier 3)
- **Task**: "Avstem bankutskrifta (vedlagt CSV) mot opne fakturaer"
- **Result**: 33 calls, 5 errors, 124s
- **What it did**: Matched 5+ customer invoice payments, created 3 supplier payment vouchers, handled interest income, bank fees, and interest expense.
- **POSITIVE**: This is the Tier 3 bank reconciliation — agent completed it! Previously timed out at 100s.
- **Issues**: 5 errors (likely payment matching issues — paying wrong invoice amounts).

### c06c5e6c — ✅ Multi-line Invoice (French)
- **Task**: "Créez une facture pour le client Océan SARL avec trois lignes de produit"
- **Result**: 8 calls, 0 errors, 31s. Clean.
- **POSITIVE**: Used existing products by number lookup instead of creating new ones.

### 670c0623 — ⏰ TIMEOUT 490s — Foreign Currency Payment (French, Tier 2/3)
- **Task**: "Nous avons envoyé une facture de 6224 EUR à Rivière SARL... Le client a maintenant payé, mais le taux..."
- **Result**: 9 calls, 1 error, 490s timeout
- **What happened**: Found customer, invoices, currency. Got postings. Then got stuck — only 9 API calls in 490s means the LLM was thinking for most of the time without acting.
- **Same timeout issue**: LLM stuck in thinking loop.

### bcccd3ee — ⏰ TIMEOUT 590s — Ledger Error Correction (Nynorsk, Tier 3)
- **Task**: "Me har oppdaga feil i hovudboka for januar og februar 2026. Finn dei 4 feila..."
- **Result**: 31 calls, 0 errors, 590s timeout
- **What happened**: Got all postings, looked up accounts, examined vouchers, fetched individual postings (13+ GET /ledger/posting/{id} calls). Spent enormous time analyzing but NEVER CREATED ANY CORRECTION VOUCHERS.
- **Issue**: Agent spent all time reading data but ran out of time before writing corrections. 30 GET calls, 0 POST calls.
- **Root cause**: The LLM is too thorough in analysis — it examines every posting individually instead of identifying errors and acting quickly.

### b32b453b — ✅ Monthly Closing (German, Tier 2/3)
- **Task**: "Führen Sie den Monatsabschluss für März 2026 durch. Buchen Sie die Rechnungsabgrenzung (7550 NOK)..."
- **Result**: 18 calls, 0 errors, 71s. Clean.
- **POSITIVE**: Created month-end voucher with all required postings.

### 9103da2b — ⏰ TIMEOUT 491s — Foreign Currency Payment (English, Tier 2/3)
- **Task**: "We sent an invoice for 2052 EUR to Northwave Ltd when rate was 10.97 NOK/EUR. Customer has now paid, but rate..."
- **Result**: 8 calls, 1 error, 491s timeout
- **Error**: Used `dateFrom/dateTo` on GET /invoice instead of `invoiceDateFrom/invoiceDateTo` on final attempt.
- **Same issue**: LLM stuck in thinking loop — only 8 API calls in 491s.

### 19a9a2d5 — ✅ Create Employee (Nynorsk)
- **Task**: "Opprett Torbjørn Neset som tilsett med e-post..."
- **Result**: 3 calls, 0 errors, 26s. Clean.
- **NEGATIVE**: Did NOT try to grant admin role (task may not have asked for it, or POST /employee/entitlement wasn't attempted).

### 0c33cf67 — ✅ Receipt/Voucher booking (German)
- **Task**: "Wir benötigen die Forretningslunsj-Ausgabe aus dieser Quittung in der Abteilung Markedsføring"
- **Result**: 12 calls, 0 errors, 66s. Clean.

### 0e74b55f — ✅ Create Customer (French)
- **Task**: "Créez le client Montagne SARL..."
- **Result**: 1 call, 0 errors, 11s. Clean.

## V3 Error Summary

| Issue | Runs affected | Type |
|-------|--------------|------|
| ⏰ LLM stuck in thinking loop (no API calls, timeout) | cfc70ffc, 670c0623, 9103da2b | **NEW — CRITICAL** |
| ⏰ Too thorough analysis, never acts (all GETs, no POSTs) | bcccd3ee | **NEW — CRITICAL** |
| employmentType at root level (should be in employmentDetails) | cfc70ffc, db25f6e3 | Known (field invention) |
| Wrong invoice date params (dateFrom instead of invoiceDateFrom) | 9103da2b | **NEW** |
| remunerationType "FIXED_SALARY" wrong enum | db25f6e3 | Known (field invention) |

## V3 Key Findings

### CRITICAL NEW ISSUE: LLM thinking loops causing timeouts
3 of 13 runs (23%) timed out because the LLM spent 400-500s **thinking** between API calls. The `time_budget=270` only checks between iterations, but the LLM itself takes the time. This is NOT an API error or a field name issue — it's the LLM getting stuck reasoning about complex tasks (foreign currency, error correction) without making progress.

**Root cause**: For complex Tier 2/3 tasks, the LLM enters a reasoning loop where it's unsure what to do next. Each LLM call takes 10-30s, and it makes many iterations without producing tool calls.

### What's working well:
- Division creation: ✅ works online (4f488011)
- Salary pipeline: ✅ works online (4f488011)
- dateFrom/dateTo on ledger/posting: ✅ works online (bcccd3ee, b32b453b)
- Simple tasks (customer, invoice, voucher): ✅ fast and clean
- Bank reconciliation: ✅ completed for first time! (ac00b88a, 124s)
- PDF extraction: ✅ works (db25f6e3)

### What still fails:
1. **LLM thinking loops** — biggest problem, causes 3/13 timeouts
2. **Foreign currency tasks** — LLM doesn't know how to handle agio/disagio
3. **Ledger error correction** — LLM analyzes but never writes corrections (runs out of time)
4. **Employment field names** — still inventing wrong fields

## V3 Deeper Analysis — Why the LLM gets stuck

### Pattern: Foreign Currency Payment (Tier 2/3) — 2/2 timeout
**What varies per variant**: Currency (EUR/USD/GBP), amounts, exchange rates, customer name, language.
**What's ALWAYS the same**:
1. An invoice exists in foreign currency at an old exchange rate
2. Customer has paid at a different rate
3. Need to: register payment + book exchange rate difference as agio (8060) or disagio (8160)

**Why LLM gets stuck**: It gathers all the data (customer, invoice, voucher postings, currencies) in ~30s but then can't figure out the accounting math. It needs to:
- Calculate: `paidAmountNOK = invoiceAmountForeignCurrency × newRate`
- Calculate: `originalAmountNOK = invoiceAmountForeignCurrency × oldRate`
- Difference = agio (if paid more) or disagio (if paid less)
- Register payment with paidAmount in NOK
- Post voucher: debit 1920 (bank) for actual NOK received, credit 1500 (customer receivable) for original NOK amount, and debit 8160 or credit 8060 for the difference

**Reproduced on sandbox (before fix)**: 34 calls, 153s. Agent wasted ~20 calls examining postings.
**Root cause confirmed**: System prompt had ZERO guidance on foreign currency accounting.
**Fix applied**: Added `**Foreign Currency Payment**` workflow to system_prompt.py with general pattern for all FX variants.
**Validated on sandbox (after fix)**: 17 calls, 89s, 0 errors (down from 34 calls, 153s). Agent followed the workflow: GET customer → GET invoice → GET paymentType → PUT payment → GET voucherType + account 8060 → POST agio voucher.
**Efficiency issue**: Still 17 calls (optimal ~7). The LLM does ~10 extra verification GETs (examining postings, checking open posts). Added stronger efficiency rule #10 ("do NOT verify your work with extra GET calls"). Second test still showed excess GETs — likely because persistent sandbox has dirty state from previous tests confusing the LLM. On fresh competition sandbox with clean data, call count should be lower.
**Note**: Cannot fully validate efficiency on persistent sandbox — dirty state causes the LLM to investigate existing payments. Real test is online with fresh sandbox.

### 🟢 FIXED-VALIDATED-SANDBOX — Ledger Error Correction (Tier 3) — 1/1 timeout
**What varies per variant**: Which accounts have errors, what type of errors, specific amounts, language.
**What's ALWAYS the same**:
1. Prompt describes N errors to find (usually 4)
2. Errors are in a specific date range (usually Jan-Feb)
3. Error types: wrong account, wrong amount, duplicate voucher, missing VAT
4. Need to: find each error → create correction voucher (reverse wrong + post correct)

**Original problems**:
- LLM fetches ALL postings and individual posting details (30 GET calls) but never creates corrections
- Even after fix v1 (workflow rewrite), LLM still fetched 4 individual postings via GET /ledger/posting/{id} after already having the bulk results
- LLM changed account from 7100→6860 when only the amount was wrong (minor accuracy issue)

**Fix applied** (system_prompt.py, Ledger Error Correction workflow):
- Added STRICT RULES section with 3 explicit rules:
  - A) NEVER call GET /ledger/posting/{id} — you already have all postings from the bulk call
  - B) Only correct EXACTLY what the error says — if amount is wrong, keep same accounts; if account is wrong, keep same amounts
  - C) Work through errors one at a time, prioritize creating corrections

**Validated on sandbox (2026-03-21)**:
- `GET /ledger/posting?voucherId=ID&dateFrom=X&dateTo=Y` → 200, returns all postings in 1 call ✅
- `POST /ledger/voucher` with 4-line correction (reverse wrong amounts + add correct amounts, same accounts) → 201 ✅
- Full correction flow: 3 API calls total (find voucher → bulk postings → create correction), zero individual posting fetches
- Correction voucher structure validated: reverse postings negate amounts, correct postings use same accounts with fixed amounts

### Pattern: Employee from PDF (Tier 3) — 1/2 timeout
**What varies per variant**: Employee details, department, language, employment fields.
**What's ALWAYS the same**:
1. PDF contains employment contract with employee details
2. Need to: create employee → create employment → set employment details

**Why LLM gets stuck on some variants**: When the PDF mentions specific employment fields (occupation code, working hours, etc.), the LLM tries to set them but guesses wrong field names, then enters a retry loop. The successful variant (db25f6e3, 90s) had simpler employment details.

**Suggested fix**: Add employment details field list to system prompt so the LLM knows which fields actually exist: `annualSalary`, `hourlyWage`, `percentageOfFullTimeEquivalent`, `employmentType`, `employmentForm`, `remunerationType`, `workingHoursScheme`, `occupationCode:{id}`. Not: `workingHoursPerWeek`, `standardWorkingHours`, `shiftDurationHours`.

### 🟢 FIXED-VALIDATED-SANDBOX — Batching for Efficiency

**Status**: Fixed and validated on sandbox (2026-03-21).

**What was added**:
- 7 batch `/list` endpoints added to `system_prompt.py` endpoint table
- Rule 15 added: prefer batch endpoints when creating/updating multiple items of the same type

**Sandbox validation results**:
| Endpoint | Status | Result |
|----------|--------|--------|
| `POST /product/list` | ✅ 201 | Batch-created products successfully |
| `POST /department/list` | ✅ 201 | Batch-created 2 departments |
| `POST /supplier/list` | ✅ 201 | Batch-created 2 suppliers |
| `POST /employee/list` | ✅ 201 | Batch-created 2 employees |
| `POST /ledger/account/list` | ✅ 201 | Batch-created 2 accounts |
| `POST /timesheet/entry/list` | ✅ exists | 404 = bad refs, endpoint accessible (not 403 BETA) |
| `POST /order/orderline/list` | ✅ exists | 422 validation = endpoint accessible, needs valid order |
| `POST /ledger/voucher/list` | ❌ 405 | Method Not Allowed — PUT only (update existing, not create). Removed from prompt. |

**Available non-BETA batch endpoints**: `POST /product/list`, `POST /department/list`, `POST /employee/list`, `POST /ledger/account/list`, `POST /activity/list`, `POST /supplier/list`, `POST /contact/list`, `POST /order/orderline/list`, `POST /timesheet/entry/list`, `PUT /travelExpense/cost/list`, `POST /division/list`. Note: `PUT /ledger/voucher/list` is update-only (requires existing IDs), not useful for batch creation.

**Where batching helps — efficiency scoring:**
The competition gives bonus points for fewer API calls + zero errors when correctness=1.0. Batching directly improves this:
- Creating 3 products: 3 calls → 1 call with `POST /product/list`
- Creating 3 departments: 3 calls → 1 call with `POST /department/list`
- Creating multiple accounts: N calls → 1 call with `POST /ledger/account/list`

**Priority**: MEDIUM — improves efficiency score but doesn't fix critical timeout issues.

### Also: Increase prompt preview to 300 chars
Current 150 chars truncates important task details. Should increase to capture more of the error descriptions and task specifics.

---

# V1 ANALYSIS — First deployment (revision 00038)

**Deployment time**: ~14:37 UTC
**Total runs analyzed**: 30 (runs 31–60)
**Source**: Cloud Run logs for `tripletex-agent` in `europe-north1`

**Important context**: Each of the 30 task types has 56 variants (7 languages × 8 data sets). It is highly unlikely to see the exact same prompt/data twice. This means:
- Errors observed here may not reproduce identically on the next run of the same task type
- Fixes must be **general** (e.g. "always include dateFrom/dateTo") rather than value-specific
- A fix validated on one variant in sandbox is not guaranteed to work on all 8 data variants online
- Specific fixes (like exact field names) are still valuable when they appear repeatedly across different runs/variants

---

## Summary by Outcome

| Outcome | Count | Run IDs |
|---------|-------|---------|
| Clean success (0 errors) | 8 | 31, 34, 43, 46, 54, 55, 59 |
| Success with minor errors | 10 | 32, 35, 36, 38, 40, 42, 45, 50, 53, 56 |
| Time budget exhausted (caused by 100s bug) | 9 | 33, 37, 39, 41, 44, 49, 51, 52, 58 |
| High error count (8+) | 3 | 48, 49, 51 |

---

## Recurring Error Patterns

### 1. `GET /ledger/posting` missing dateFrom/dateTo (MOST COMMON — 12+ occurrences)
**Runs affected**: 33, 39, 42, 48, 50, 52
**Error**: `"dateFrom": "Kan ikke være null"`, `"dateTo": "Kan ikke være null"`
**What happens**: LLM calls `/ledger/posting` with only `voucherId` param but omits the REQUIRED `dateFrom` and `dateTo` params. It then retries with dates but wastes 1-2 API calls each time.
**Impact**: Wastes calls and time, especially on Tier 3 ledger tasks where many voucher postings need examining.
**Root cause**: System prompt mentions `GET /ledger/posting` but does NOT state that `dateFrom` and `dateTo` are REQUIRED params.

### 2. `POST /division` failures (6+ occurrences)
**Runs affected**: 33, 36, 48
**Errors**:
- `"organizationNumber": "Feltet må fylles ut"` — org number required
- `"municipalityDate": "Feltet må fylles ut"` — municipality date required
- `"municipality": "Må velges"` — municipality required
- `"Juridisk enhet kan ikke registreres som virksomhet/underenhet"` — can't use company's own org number

**What happens**: Agent tries to create division without required fields. Then retries with the company's own org number which is rejected. Finally tries a random number.
**Impact**: 2-3 wasted calls per salary task. Division creation is a prerequisite for employment/salary.
**Root cause**: `apply_fixes.py` `_ensure_division()` doesn't include required fields. System prompt doesn't document division creation requirements.

### 3. `POST /employee/employment` field errors (4+ occurrences)
**Runs affected**: 36, 48, 49
**Errors**:
- `"employmentForm": "Feltet eksisterer ikke i objektet"` — wrong field name
- `"startDate": "Feltet eksisterer ikke i objektet"` — sometimes rejected
- `"employee.dateOfBirth": "Feltet må fylles ut"` — dateOfBirth required on employee before employment

**What happens**: LLM uses wrong field names for employment creation. The `employmentForm` field should be inside `employmentDetails`, not at root level.
**Impact**: Salary tasks fail or require many retries.

### 4. `GET /balanceSheet` missing dateFrom/dateTo (3+ occurrences)
**Runs affected**: 39, 40, 45, 46
**Error**: Uses `?date=` or `?dateOn=` or `?dateFrom=&dateTo=` as separate request — all require both `dateFrom` AND `dateTo`.
**Impact**: Wasted calls on Tier 3 year-end/reconciliation tasks.

### 5. `POST /product` — product number already exists (3 occurrences in run 45)
**Runs affected**: 45
**Error**: `"Produktnummeret XXXX er i bruk"`
**What happens**: Sandbox has pre-existing products with the same numbers. LLM should GET first.
**Impact**: 3 wasted calls, then has to GET existing products.

### 6. `POST /ledger/voucher` — unknown fields (2+ occurrences)
**Runs affected**: 42
**Error**: `"dueDate": "Feltet eksisterer ikke i objektet"`
**Impact**: LLM invents fields that don't exist on the voucher model.

### 7. `POST /travelExpense/cost` — wrong field names (3+ occurrences)
**Runs affected**: 56, 57, 58
**Error**: `"amount": "Feltet eksisterer ikke i objektet"` — should be `amountCurrencyIncVat`
**Impact**: Travel expense costs fail, wastes 1-2 calls per cost item.

### 8. `POST /travelExpense/perDiemCompensation` — field errors
**Runs affected**: 58
**Errors**: Various field mapping failures
**Impact**: Per diem compensation never successfully created.

### 9. `GET /travelExpense/rate` — result set too large
**Runs affected**: 58
**Error**: `"Result set too large. Limit of 10000 reached"`
**Impact**: LLM can't query rates without more specific filters.

---

## Task-Level Analysis (by inferred task type)

### Tier 1 Tasks — Generally working well

**Credit Note (Run 31)**: ✅ 3 calls, 0 errors, 22s. Clean execution.

**Create Departments (Run 46)**: ✅ 3 calls, 0 errors, 17s. Clean.

**Create Customer (Run 54)**: ✅ 0 tool calls visible (likely 1-2 actual), 14s. Clean.

**Create+Send Invoice (Run 55)**: ✅ 8 calls, 0 errors, 35s. Clean flow: customer→product→order→invoice→send.

### Tier 2 Tasks — Mixed results

**Employee + Employment Details (Run 32)**: ⚠️ 9 calls, 1 error, 72s.
- Failed: `workingHoursPerWeek` field doesn't exist on employment details
- Had to retry with correct fields
- Eventually completed but slow

**Complex Multi-task (Run 33)**: ❌ TIMEOUT at 101s (100s bug), 14 calls, 3 errors.
- Tried to do TOO MANY things: department creation, employee, invoice lookup, division creation, project, timesheet, employment details
- Division creation failed twice
- Ran out of time before completing everything
- This appears to be a Tier 3 task (hourly billing + multi-step)

**Send Reminder/Invoice + Payment (Runs 36, 38)**: ⚠️ Multiple errors with division creation.
- Run 36: 13 calls, 0 final errors but 3 intermediate errors, 60s
- Run 38: 15 calls, 1 error, 56s
- Both tried to create purregebyr (reminder fee) products and invoices
- Division creation wastes time

**Supplier Invoice with Voucher (Run 42)**: ⚠️ 8 calls, 1 error, 61s.
- Voucher failed first time (`dueDate` field doesn't exist)
- Eventually created but slow
- Also created unnecessary projects and activities

**Multi-product Invoice (Run 45)**: ⚠️ 11 calls, 3 errors, 53s.
- All 3 product numbers already existed → 3 wasted POST calls
- Had to GET existing products instead
- Eventually completed with invoice

**Invoice Payment (Run 59)**: ✅ 7 calls, 0 errors, 36s. Clean.

### Tier 2 Tasks — COMPLETELY FAILING

**Salary/Payroll (Run 48)**: ❌ 13 calls, 0 final but 11 intermediate errors, 89s.
- Salary transaction failed: "Ansatt ikke registrert med arbeidsforhold i perioden"
- Division creation failed multiple times
- Employment creation failed: "dateOfBirth: Feltet må fylles ut"
- Eventually gave up on salary, started doing unrelated things (supplier lookup, vouchers)
- **Score likely 0** — salary was never successfully posted

**Salary/Payroll continuation (Run 49)**: ❌ TIMEOUT at 101s (100s bug), 18 calls, 8 errors.
- Continuation of Run 48's failures
- Still failing on employment creation

### Tier 3 Tasks — LOW SCORES

**Year-End Closing / Depreciation (Run 39)**: ⚠️ TIMEOUT at 101s (100s bug), 29 calls, 2 errors.
- Complex task: depreciation vouchers, prepaid rent dissolution, balance sheet checking
- Created multiple accounts that didn't exist (1209, 8700)
- Posted 4 depreciation/adjustment vouchers
- Ran out of time doing balance sheet verification
- Also tried to create reminder fee and send invoice (mixed tasks from same sandbox)
- **Likely partial score** — some vouchers correct but might have wrong amounts or accounts

**Ledger Error Correction (Runs 50-51)**: ⚠️ TIMEOUT at 115s (100s bug), 38 calls, 5 errors.
- Run 50: Found vouchers, analyzed postings, created project, recorded timesheet, posted supplier cost voucher, created product + order + invoice (20 calls, 4 errors, 72s)
- Run 51: Tried to DELETE a voucher (failed — "Bilag kan ikke slettes"), then created 4 correction vouchers (6 calls, 1 error, timeout)
- **Main issue**: Can't delete existing vouchers, has to create correction vouchers
- **Time issue**: Too many GET calls to examine vouchers, then runs out of time for corrections
- Repeated `GET /ledger/posting` without dates wastes calls

**Foreign Currency Invoice + Payment (Run 52-53)**: ⚠️ TIMEOUT at 111s+104s (100s bug), 12+13 calls.
- Run 52: Found customer, invoices, looked up currency EUR. Spent time examining voucher postings.
- Run 53: Created departments, posted correction voucher for payment with agio (exchange rate difference)
- Timeout before completing all required work
- **Issue**: The task involves EUR→NOK conversion and exchange rate differences (agio/disagio) — the LLM doesn't know account 8060 (Agio) needs to be used

**Travel Expense (Runs 56-58)**: ⚠️ Multiple sub-tasks spanning 3 runs.
- Run 56: Created travel expense, set travel details, started costs. Errors on voucher fields and cost fields. 19s, 2 errors.
- Run 57: Continued with costs. 1 error on cost amount field. 58s.
- Run 58: Still working on per diem and costs. Rate query returned 10000+ results. TIMEOUT at 103s (100s bug), 5 errors.
- **Issues**:
  1. `amount` instead of `amountCurrencyIncVat` on costs (fixed in system prompt but maybe not deployed?)
  2. Per diem compensation field mapping failures
  3. `/travelExpense/rate` returns too many results without filters

---

## Critical Findings for Tier 3 Improvement

### Problem 1: Time Budget Exhaustion (NOW FIXED)
9 of 30 runs hit the old 100s time budget (which was a code bug — competition allows 300s). This has been fixed to 270s. However, even with more time, the underlying causes still waste API calls:
- Too many GET calls to examine ledger data
- Retry loops on division/employment creation
- Querying the same endpoints multiple times with slightly different params

### Problem 2: Division Creation is a Bottleneck
Division creation requires `organizationNumber`, `municipality`, `municipalityDate` — 3 fields the LLM doesn't know about. Every salary/employment task wastes 2-3 calls discovering this. The `_ensure_division()` helper in `apply_fixes.py` also fails for the same reason.

### Problem 3: `/ledger/posting` Always Needs Date Range
The LLM repeatedly forgets `dateFrom`/`dateTo` on ledger posting queries. This is the #1 most repeated error. Every Tier 3 ledger task is affected.

### Problem 4: Travel Expense Cost Field Names
The field `amountCurrencyIncVat` (not `amount`) is consistently wrong. This suggests the system prompt fix wasn't deployed or the LLM ignores it.

### Problem 5: Vouchers Can't Be Deleted
`DELETE /ledger/voucher/{id}` fails with "Bilag kan ikke slettes". The agent should create CORRECTION vouchers (reversal entries) instead of trying to delete.

### Problem 6: Year-End Tasks are Very Complex
The LLM is doing the right things (depreciation, prepaid rent dissolution, tax provisioning) but:
- Spends too many calls looking up accounts one at a time
- Creates accounts that might already exist
- Runs out of time before completing all required entries

### Problem 7: Foreign Currency Handling
The agent doesn't know about agio/disagio accounts (8060/8160) for exchange rate differences. It spends time trying to figure out the correct accounting treatment.

---

## Scores Context (from user)
- 3 Tier 2 tasks fail completely (score 0)
- 1 Tier 3 task fails completely (not prioritized — no other team solved it)
- Tier 3 scores are very low — need to reach 6.0 (perfect)
- Tier 3 tasks: Employee from PDF, Bank Reconciliation, Ledger Error Correction

---

## Recommended Priority for Investigation
1. **Salary pipeline** (division → employment → salary transaction) — causes complete failures
2. **`/ledger/posting` date requirement** — wastes calls on every Tier 3 task
3. **Travel expense cost fields** — prevents travel task completion
4. **Year-end/depreciation task efficiency** — too many calls, needs streamlining
5. **Voucher deletion → correction voucher** guidance
6. **`/balanceSheet` date requirement** — same pattern as ledger/posting

---

## CORRECTION: Time Budget

The deployed code had `time_budget = 100` which was a bug — the competition allows **300 seconds** (5 minutes). The Cloudflare 120s issue mentioned on Slack only affects teams who self-host via Cloudflare tunnels — we use Cloud Run with direct HTTPS so we get the full 300s.

**Fixed**: `time_budget` changed from 100 → **270** (30s margin before 300s hard cutoff). All 9 timeouts in the analyzed runs were caused by this bug — they would have had time to finish with the corrected budget.

---

## Deep API Investigation (OpenAPI spec + sandbox testing)

### Finding 1: BETA ENDPOINTS RETURN 403 IN COMPETITION (CONFIRMED)

**Source: Official Slack announcement from Erik (Astar):**
> Most 403 errors are caused by using API endpoints that are marked as [BETA]. One endpoint alone accounted for 73% of all 403 errors.
> "You get 403 from BETA endpoints." — Erik

**This means `PUT /employee/entitlement/:grantEntitlementsByTemplate` WILL return 403.** This is the endpoint we use to grant admin rights — worth 50% of the employee task score.

**CRITICAL BETA endpoints we must NOT use:**
- `PUT /employee/entitlement/:grantEntitlementsByTemplate` — grant admin (403)
- `PUT /employee/entitlement/:grantClientEntitlementsByTemplate` — grant client admin (403)
- `PUT /project/{id}` — update project (403)
- `DELETE /project/{id}` — delete project (403)
- `DELETE /customer/{id}` — delete customer (403)
- `PUT /order/orderline/{id}` — update order line (403)

**Alternative for admin rights:** UNKNOWN. All entitlement-write endpoints are BETA. The competition organizer says "that should be enough to solve the task" — implies either:
  a) The employee task doesn't actually require admin rights on competition sandboxes, OR
  b) There's a non-API way (like setting `userType` or a specific role field on employee creation), OR
  c) The entitlement endpoint is specifically whitelisted despite being BETA

**Action needed:** Investigate if setting `userType: "ADMINISTRATOR"` or similar on POST /employee achieves admin access without the BETA endpoint.

**Sandbox testing results — NON-BETA ALTERNATIVE FOUND:**
- `userType` on POST /employee only accepts: STANDARD, EXTENDED, NO_ACCESS (all map to userType=None internally)
- **SOLUTION FOUND**: `POST /employee/entitlement` is NOT marked as BETA!
  - Body: `{"employee": {"id": <empId>}, "customer": {"id": <companyId>}, "entitlementId": 1}`
  - `entitlementId: 1` = ROLE_ADMINISTRATOR
  - `companyId` is available from the POST /employee response or GET /employee response
  - Verified on sandbox: grants ROLE_ADMINISTRATOR successfully
- Use `userType: "EXTENDED"` on POST /employee (gives base entitlements), then POST entitlement for admin
- The BETA `PUT /employee/entitlement/:grantEntitlementsByTemplate` should be avoided as a primary method

### Finding 2: Cloudflare 120s tunnel timeout — DOES NOT APPLY TO US
The Slack announcement mentions "Cloudflared tunnel timeouts after 120 seconds". This only affects teams who self-host via Cloudflare tunnels. **We use Cloud Run with direct HTTPS — our timeout is the full 300 seconds.**

### Finding 3: `/incomingInvoice` (BETA) — DO NOT USE
`POST /incomingInvoice` is BETA and will return 403. Continue using `/ledger/voucher` for supplier invoices.

### Finding 4: Travel Expense API — Correct Workflow Discovered
Through sandbox testing, the correct travel expense workflow is:

1. **POST /travelExpense** — creates as type=1 (employee expense) by default
2. **PUT /travelExpense/{id}/convert** — converts to type=0 (travel report). REQUIRED for per diem.
3. **PUT /travelExpense/{id}** — set `travelDetails` object: `{departureDate, returnDate, destination, isDayTrip: false, isForeignTravel: false, isCompensationFromRates: true}`. travelDetails only exists on type=0.
4. **GET /travelExpense/rate?type=PER_DIEM&dateFrom=X&dateTo=Y** — find valid rate categories for the travel dates
5. **POST /travelExpense/perDiemCompensation** — fields: `travelExpense:{id}, rateCategory:{id}, overnightAccommodation:"HOTEL", location:"City", count:N`
6. **POST /travelExpense/cost** — fields: `travelExpense:{id}, costCategory:{id}, paymentType:{id}, currency:{id}, amountCurrencyIncVat:N, date:"YYYY-MM-DD"`. NO `description` or `amount` field.

**Key discoveries:**
- `travelDetails` is an **object field on the travel expense** (not a separate endpoint)
- It only exists on **type=0** (travel report), not type=1 (employee expense)
- Must **convert** from type=1 to type=0 before setting travelDetails
- Per diem rate categories are **date-dependent** — must query `/travelExpense/rate?dateFrom=X&dateTo=Y` to find valid ones
- Cost field is `amountCurrencyIncVat` (NOT `amount`, NOT `amountCurrency`, NOT `description`)

### Finding 5: Division Creation — Required Fields
From sandbox testing, `POST /division` requires:
- `name` (string)
- `startDate` (YYYY-MM-DD)
- `organizationNumber` (string, CANNOT be the company's own org number — use a random 9-digit number)
- `municipalityDate` (YYYY-MM-DD)
- `municipality` (object: `{id: N}` — get from `GET /municipality`, or use `{id: 301}` for Oslo)

### Finding 6: `GET /ledger/posting` — dateFrom/dateTo ALWAYS required
Confirmed in OpenAPI spec: `dateFrom` and `dateTo` are marked `required=True`. The LLM repeatedly forgets these, wasting 1-2 calls per Tier 3 task.

### Finding 7: `GET /balanceSheet` — dateFrom/dateTo ALWAYS required
Same as ledger/posting. Both params are required. The LLM tries `?date=` or `?dateOn=` which don't exist.

### Finding 8: Travel expense cost — NO `description` field
The field `description` does NOT exist on the cost model. Causes "Feltet eksisterer ikke" error. The cost only needs: `travelExpense`, `costCategory`, `paymentType`, `currency`, `amountCurrencyIncVat`, `date`.

### Finding 9: Per diem requires valid rate category for date range
Rate categories are year-specific. Must query `/travelExpense/rate?type=PER_DIEM&dateFrom=X&dateTo=Y` to get categories valid for the travel dates. Using old category IDs (like 11) fails with "dato samsvarer ikke med valgt satskategori".

---

## Code Changes Applied

Status labels:
- **🟢 FIXED-VALIDATED-SANDBOX**: Code changed AND verified working on sandbox. Not yet validated in competition.
- **🟡 FIXED-NOT-VALIDATED**: Code changed but not reproduced/validated on sandbox yet.
- **🔵 ANALYZED**: Problem reproduced and root cause found. Fix designed but not applied to code.
- **⚪ NOT YET ANALYZED**: Known problem, not yet investigated in depth.

### 🟢 FIXED-VALIDATED-SANDBOX + ✅ CONFIRMED_ONLINE — Time budget (agent.py)
- **Problem**: Deployed code had `time_budget = 100` (a bug) — competition allows 300s via Cloud Run
- **Fix**: Changed to `time_budget = 270` (30s margin before 300s hard cutoff)
- **Validated sandbox**: Confirmed locally that agent runs past 100s.
- **✅ CONFIRMED_ONLINE**: V2 Run 9 ran for 196s and completed successfully. Would have timed out at 100s in v1. 0 timeouts in v2 (was 9 in v1). THIS FIX WORKS.

### 🟢 FIXED-VALIDATED-SANDBOX — Admin rights via non-BETA endpoint (system_prompt.py)
- **Problem**: `PUT /employee/entitlement/:grantEntitlementsByTemplate` is BETA → 403 in competition
- **Fix**: System prompt now instructs LLM to use `POST /employee/entitlement` with `{employee:{id}, customer:{id: companyId}, entitlementId: 1}` (not BETA)
- **Also**: Use `userType: "EXTENDED"` on POST /employee instead of "STANDARD"
- **Validated**: Tested on sandbox — `POST /employee/entitlement` successfully grants ROLE_ADMINISTRATOR (entitlementId=1)
- **Impact**: Employee admin role (50% of employee task score) should now work in competition

### 🟢 FIXED-VALIDATED-SANDBOX — DELETE tool added (agent.py)
- **Problem**: No DELETE tool for tasks like "delete travel expense"
- **Fix**: Added `tripletex_delete` tool definition and handler
- **Validated**: Created travel expense "DeleteMeViaAgent" → asked agent to delete → confirmed 404 after (deleted successfully). 13.7s, clean.
- **Impact**: Delete tasks now possible

### 🟢 FIXED-VALIDATED-SANDBOX — Salary employee field placement (apply_fixes.py)
- **Problem**: LLM puts `employee` at transaction root instead of inside payslip
- **Fix**: `apply_fixes` auto-moves `employee` from transaction root to payslip level
- **Validated**: Unit tested — employee correctly moved from root to payslip, date/year/month defaults set, count defaults set.
- **Impact**: Saves 1 retry per salary task

### 🟢 FIXED-VALIDATED-SANDBOX — Voucher defaults (apply_fixes.py)
- **Problem**: LLM forgets `description` field → 422 error → retry
- **Fix**: `apply_fixes` auto-adds `description: "Bilag"` and `date: TODAY` if missing
- **Validated**: Unit tested — description defaults to "Bilag", date defaults to today, row numbering starts at 1, amount→amountGross conversion works.
- **Impact**: Saves 1 retry per voucher task

### 🟢 FIXED-VALIDATED-SANDBOX — Endpoint list expanded (system_prompt.py)
- **Problem**: Missing endpoints for Tier 3 tasks (/ledger/posting, /balanceSheet, /division, etc.)
- **Fix**: Added 20+ endpoints from OpenAPI spec analysis
- **Validated**: Confirmed all 6 key endpoints (/ledger/posting, /balanceSheet, /division, /travelExpense/costCategory, /ledger/openPost, /bank/reconciliation) present in system prompt. Agent successfully used /ledger/posting in test task (7.6s).
- **Impact**: LLM can now discover and use endpoints it couldn't find before

### 🟢 FIXED-VALIDATED-SANDBOX — Travel expense cost fields documented (system_prompt.py)
- **Problem**: System prompt had wrong cost field names (used `amount` and `description`)
- **Fix**: Documented correct cost field (`amountCurrencyIncVat`, no `description`), added costCategory endpoint
- **Validated**: Agent created travel expense "Konferanse Oslo" with Fly cost of 4200 kr using correct `amountCurrencyIncVat` field. 32s, type=1 (costs work on type=1).
- **Note**: The `convert` step for per diem/travelDetails was fixed separately (see Fix 3 — per diem + travel expense type conversion)
- **Impact**: Cost-only travel expense tasks now work. Per diem tasks still need the convert fix.

### 🟢 FIXED-VALIDATED-SANDBOX + ✅ CONFIRMED_ONLINE — Division creation (apply_fixes.py + system_prompt.py)
- **Problem**: Both `_ensure_division()` helper and system prompt salary workflow missing required fields for POST /division
- **Fix applied** (code + prompt):
  1. **apply_fixes.py `_ensure_division()`**: Added `organizationNumber: "987654321"`, `municipalityDate: "2020-01-01"`, `municipality: {"id": 301}` to the POST payload.
  2. **system_prompt.py Salary workflow**: Updated with all required division fields + note about not using company's own org number + dateOfBirth prerequisite for employment.
- **Validated sandbox**: Unit test + agent test confirmed.
- **✅ CONFIRMED_ONLINE**: V2 Run 3 shows `POST /division {"name":"Hovedvirksomhet","startDate":"2026-01-01","organizationNumber":"123456789","municipalityDate":"2026-01-01","municipality":{"id":...}}` — succeeded on first attempt! The LLM learned the correct fields from the updated prompt. 0 division errors in v2 (was 7 in v1). THIS FIX WORKS.

### 🟢 FIXED-VALIDATED-SANDBOX + ✅ CONFIRMED_ONLINE — `/ledger/posting` and `/balanceSheet` date requirement
- **Problem**: LLM forgets dateFrom/dateTo on 12+ calls across runs (most common error, 15 total)
- **Fix applied** (system prompt):
  1. Endpoint table: `GET /ledger/posting` → "Query postings (REQUIRED params: dateFrom, dateTo)"
  2. Added `GET /ledger/posting/{id}` → "Get single posting by ID (no date params needed)"
  3. Endpoint table: `GET /balanceSheet` → "Get balance sheet (REQUIRED params: dateFrom, dateTo)"
  4. Endpoint table: `GET /ledger/openPost` → "Query open posts (REQUIRED param: date, single date)"
  5. Added critical rule #13 about required date params
  6. Updated Ledger Error Correction workflow with explicit date params
- **Validated sandbox**: Agent called `GET /ledger/posting?dateFrom=2026-01-01&dateTo=2026-01-31` on first attempt — 0 errors.
- **✅ CONFIRMED_ONLINE**: V2 runs 7-9 show ALL ledger/posting and balanceSheet calls include dateFrom/dateTo correctly. 0 date-related errors in v2 (was 15 in v1). THIS FIX WORKS.

### 🟢 FIXED-VALIDATED-SANDBOX (not triggered in v2) — Voucher deletion guidance
- **Problem**: LLM tries DELETE /ledger/voucher/{id} which fails with "Bilag X kan ikke slettes" on posted vouchers
- **Fix applied** (system prompt):
  1. Changed "Delete/Reverse Entries" to explain posted vouchers can't be deleted — must create correction vouchers with negated amounts
  2. Updated Ledger Error Correction workflow to explicitly say "do NOT delete vouchers, create correction vouchers instead"
- **Validated**: Created an error voucher (20000 kr husleie) → asked agent to correct to 15000 kr → agent created correction voucher with reversal (-20000/+20000) and correct posting (15000/-15000). 7 calls, 0 errors, 38s. **No DELETE attempted.** Also validated that dateFrom/dateTo fix (Fix 1) works in the same flow.

### 🟢 FIXED-VALIDATED-SANDBOX (not triggered in v2) — Per diem rate category date-dependency
- **Problem**: LLM uses old/hardcoded rate category IDs (e.g. id=11, expired 2008) → "dato samsvarer ikke med valgt satskategori"
- **Fix applied** (system prompt): Rewrote entire Travel Expense workflow to include per diem with filtered rateCategory query: `GET /travelExpense/rateCategory?type=PER_DIEM&isValidDomestic=true&dateFrom=X&dateTo=Y`. Added explicit note not to hardcode IDs.
- **Validated**: Agent queried rateCategory with `type=PER_DIEM&isValidDomestic=true&dateFrom=2026-03-17&dateTo=2026-03-19` → found id=740 → POST perDiemCompensation succeeded. 0 errors.

### 🔴 FAILED_ONLINE — LLM invents non-existent field names (general pattern)
- **Problem**: LLM guesses plausible but wrong field names. Variant-dependent.
- **Fix applied** (system prompt): Rule #14 tells LLM to remove rejected fields and retry. Listed known bad fields.
- **Sandbox validation**: Worked — dueDate removed and retried successfully.
- **FAILED_ONLINE**: Rule #14 partially works (dueDate recovery ok) but LLM keeps inventing NEW fields not in the list: `bankAccount` on supplier, `shiftDurationHours` on employment details, `employmentType` at root level. The rule says "do NOT guess alternatives" but the LLM still guesses before getting the error. The fix reduces retries from many to 1, but doesn't prevent the initial error.
- **Root cause deeper**: The LLM doesn't know which fields actually exist on each model. Listing bad fields in rule #14 is whack-a-mole — new variants trigger new wrong guesses. Need a more general solution.
- **V2 occurrences**: bankAccount(1), employmentType(1), dueDate(1, recovered), standardWorkingHours(1), shiftDurationHours(1) = 5 errors across 9 runs

### 🟢 COVERED BY FIX 1 — GET /ledger/openPost requires `date` param
- **Problem**: LLM calls `/ledger/openPost` without `date` param → 422.
- **Covered by**: Fix 1 added `GET /ledger/openPost` → "Query open posts (REQUIRED param: date, single date)" to endpoint table + critical rule #13 mentions it explicitly.

### 🟢 COVERED BY FIX 4 — POST /employee/employment requires employee dateOfBirth
- **Problem**: Creating employment fails if employee has no dateOfBirth set.
- **Covered by**: Fix 4 added "Ensure employee has dateOfBirth set before creating employment" to Salary workflow.

### 🟢 COVERED BY FIX 3 — GET /travelExpense/rate result set too large
- **Problem**: Unfiltered `/travelExpense/rate` returns 10000+ results.
- **Covered by**: Fix 3 rewrote travel expense workflow to use `/travelExpense/rateCategory?type=PER_DIEM&isValidDomestic=true&dateFrom=X&dateTo=Y` instead of querying rates directly.

### ⚪ NEW IN V2 — PUT /project/{id} is BETA (403 in competition)
- **Problem**: V2 Run 8 used `PUT /project/{id}` to set `isFixedPrice: true`. This endpoint is BETA → 403.
- **Impact**: Milestone invoice tasks that need to update a project can't set the fixed price flag.
- **Occurrences**: 1 in v2
- **Status**: Needs investigation — is there a non-BETA way to create a project with isFixedPrice from the start?

### ⚪ NEW IN V2 — POST /ledger/account wrong `type` enum values
- **Problem**: V2 Run 9 tried to create account 8700 (Skattekostnad) with `type: "TAXES_AND_EXTRAORDINARY_ITEMS"` and `"OTHER_EXPENSES"` — both rejected. `"OPERATING_EXPENSES"` eventually worked.
- **Impact**: 2 wasted calls per account creation when the LLM guesses wrong type enum.
- **Occurrences**: 2 errors in 1 run
- **Status**: Needs investigation — what are the valid `type` enum values?

### 🟢 FIXED-VALIDATED-SANDBOX (not triggered in v2) — Travel expense type conversion + full workflow
- **Problem**: Per diem only works on type=0, but POST creates type=1. travelDetails silently ignored on type=1. No error to guide the LLM.
- **Fix applied** (system prompt):
  1. Rewrote entire Travel Expense workflow: POST → convert → PUT travelDetails → costs → per diem
  2. Added `/travelExpense/{id}/convert` to endpoint table
  3. Removed incorrect `description` field from cost docs
  4. Added `amountCurrencyIncVat` emphasis and note that `amount`/`description` don't exist on costs
- **Validated**: Full end-to-end test — agent executed: POST travelExpense → PUT convert → PUT travelDetails(dep/ret/dest) → POST cost(Fly 3800) → POST cost(Hotell 3000) → POST perDiemCompensation(rateCategory=740, overnight). **16 calls, 0 errors, 43s.** Previously travel expense spanned 3 runs with 8+ errors and timed out.
