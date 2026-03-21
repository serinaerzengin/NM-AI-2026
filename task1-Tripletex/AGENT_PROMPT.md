# Build a Winning Tripletex Accounting Agent — Complete Briefing

You are being asked to build an AI agent for the **NM i AI 2026** (Norwegian AI Championship) competition. This document contains EVERYTHING you need — competition rules, architecture decisions, domain knowledge, API details, known errors, and our battle-tested strategy from ~150 production submissions. Read it carefully.

**Your role**: You are a fresh agent starting from scratch. We've learned a LOT from previous attempts and want you to build the best possible solution. If anything here seems wrong or you have a better idea, speak up — we welcome improvements. But please respect the warnings about errors we've actually encountered in production.

**If you need something from me** (like downloading files, running commands, checking the API docs, etc.), just ask step by step and I'll do it.

---

## 1. COMPETITION OVERVIEW

### What we're building
A web service (Docker → Cloud Run) that receives accounting task prompts in 7 languages and executes them against a Tripletex sandbox API. Each submission gets a **fresh sandbox** (no state carries over between submissions).

### Scoring
```
score = correctness × tier_multiplier + efficiency_bonus
```
- `correctness` = fields_correct / fields_total (0.0–1.0)
- `tier_multiplier` = 1 (Tier 1), 2 (Tier 2), 3 (Tier 3)
- `efficiency_bonus` = only awarded if correctness == 1.0, based on fewer API calls and zero 4xx errors. Can up to DOUBLE the score.

**Key insight**: A perfect efficient Tier 2 task = 4.0 points. An 80%-correct Tier 2 = 1.6 points. **Correctness is king**, and 100% correctness unlocks the efficiency bonus which can double your score.

### Task structure
- **30 task types**, each with **56 variants** (7 languages × 8 data variations)
- The WORKFLOW for each task type is deterministic — only the entity names/numbers/amounts change
- Languages: Norwegian (Bokmål/Nynorsk), English, German, French, Spanish, Swedish, Finnish

### Point distribution
| Tier | Tasks | Max per task | Total possible |
|------|-------|-------------|----------------|
| Tier 1 | ~8 tasks | 2.0 | ~16 |
| Tier 2 | ~19 tasks | 4.0 | ~76 |
| Tier 3 | ~3 tasks | 6.0 | ~18 |
| **Total** | **30** | | **~110** |

### Time limits
- **5 minutes** per task (hard timeout)
- Budget for **110 seconds** max to leave safety margin
- LLM calls take 5-15 seconds each

### API endpoint
Our service receives: `POST /solve` with `{"prompt": "...", "files": [...], "tripletex_api": {"base_url": "...", "token": "..."}}`.

---

## 2. ARCHITECTURE DECISION: Tool-Calling Agent

We tried **plan-then-execute** (LLM generates a JSON plan with $placeholder variables, code executes blindly). It failed badly because:
- Placeholder resolution breaks constantly (`$customer_id` vs `$create_customer_values_0_id`)
- If step 2 fails, steps 3-7 cascade fail (unresolved placeholders)
- LLM can't see real API responses when planning — guesses field names wrong
- Fixing requires another LLM call which often makes things worse

### The winning approach: LLM with direct tool access

```
POST /solve
  → LLM receives: task prompt + files + system prompt with accounting knowledge
  → LLM has tools: tripletex_get, tripletex_post, tripletex_put
  → LLM calls tools one at a time, sees real responses, adapts
  → Loop until done or time budget exhausted
  → Return {"status": "completed"}
```

**Why this wins**:
| Aspect | Plan-then-execute | Tool-calling |
|--------|-------------------|-------------|
| Variable resolution | Symbolic placeholders — breaks | LLM sees actual ID 42, uses it |
| Error recovery | Separate "fix" LLM call | LLM reads error, adapts naturally |
| Adaptation | Rigid plan | Sees GET returns empty → POSTs instead |
| Speed | 2+ LLM calls before execution | Starts executing immediately |
| Tier 3 tasks | Nearly impossible | Natural — LLM queries, analyzes, acts |

### Implementation sketch

```python
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel

@function_tool
async def tripletex_get(ctx, path: str, params: str = "{}") -> str:
    """GET request to Tripletex API. Returns JSON response."""
    result = await client.call("GET", path, params=json.loads(params))
    return format_response(result)

@function_tool
async def tripletex_post(ctx, path: str, body: str = "{}") -> str:
    """POST request. Body is validated and silently fixed before sending."""
    payload = json.loads(body)
    payload = apply_fixes(path, "POST", payload)
    errors = validate(path, payload)
    if errors:
        return f"VALIDATION ERROR (not sent): {errors}"
    result = await client.call("POST", path, json=payload)
    return format_response(result)

@function_tool
async def tripletex_put(ctx, path: str, body: str = "{}", params: str = "{}") -> str:
    """PUT request. For updates and action endpoints (/:invoice, /:payment)."""
    payload = json.loads(body) if body != "{}" else None
    if payload:
        payload = apply_fixes(path, "PUT", payload)
    result = await client.call("PUT", path, json=payload, params=json.loads(params))
    return format_response(result)

agent = Agent(
    name="TripletexAccountant",
    model=LitellmModel(model="gemini/gemini-3.1-pro-preview"),
    tools=[tripletex_get, tripletex_post, tripletex_put],
    instructions=SYSTEM_PROMPT,
)

result = await Runner.run(agent, input=task_prompt, context=ctx, max_turns=30)
```

### The `apply_fixes` function — our hard-won knowledge

This function silently corrects every mistake the LLM consistently makes. **This is where all our battle scars become an advantage.**

```python
def apply_fixes(path, method, payload):
    # === VOUCHER FIXES (most critical) ===
    if "/voucher" in path and "postings" in payload:
        for i, p in enumerate(payload["postings"]):
            # Row MUST start at 1 (row 0 is system-reserved → instant 422)
            p["row"] = i + 1
            # LLM uses "amount" but API requires "amountGross" + "amountGrossCurrency"
            amt = p.get("amountGross") or p.get("amount") or p.get("amountGrossCurrency")
            if amt is not None:
                p["amountGross"] = amt
                p["amountGrossCurrency"] = amt
                p.pop("amount", None)

    # === ORDER FIXES ===
    if path == "/order" and method == "POST":
        payload.setdefault("deliveryDate", payload.get("orderDate", TODAY))
        payload.setdefault("orderDate", TODAY)
        # Strip vatType from order lines (inherited from product, causes errors if set)
        for line in payload.get("orderLines", []):
            line.pop("vatType", None)

    # === PRODUCT FIXES ===
    if path == "/product" and method == "POST":
        price_ex = payload.get("priceExcludingVatCurrency")
        vat_id = payload.get("vatType", {}).get("id")
        if price_ex and "priceIncludingVatCurrency" not in payload:
            rates = {3: 0.25, 31: 0.15, 32: 0.12, 5: 0.0, 6: 0.0}
            rate = rates.get(vat_id, 0.25)
            payload["priceIncludingVatCurrency"] = round(price_ex * (1 + rate), 2)

    # === SALARY FIXES ===
    if "/salary/transaction" in path:
        payload.setdefault("date", TODAY)
        payload.setdefault("year", int(TODAY[:4]))
        payload.setdefault("month", int(TODAY[5:7]))
        for ps in payload.get("payslips", []):
            ps.setdefault("date", payload["date"])
            ps.setdefault("year", payload["year"])
            ps.setdefault("month", payload["month"])
            for spec in ps.get("specifications", []):
                # LLM uses "amount" but API requires "rate"
                if "rate" not in spec and "amount" in spec:
                    spec["rate"] = spec.pop("amount")
                spec.setdefault("count", 1)

    # === ACTIVITY FIXES ===
    if "/activity" in path and method == "POST":
        if payload.get("activityType") == "PROJECT_SPECIFIC":
            payload["activityType"] = "PROJECT_SPECIFIC_ACTIVITY"
        payload.setdefault("activityType", "PROJECT_GENERAL_ACTIVITY")

    # === EMPLOYEE FIXES ===
    if path == "/employee" and method == "POST":
        for emp in payload.get("employments", []):
            emp.setdefault("isMainEmployer", True)
            emp.setdefault("startDate", TODAY)

    # === ACCOUNTING DIMENSION FIXES ===
    if "/accountingDimensionName" in path and method == "POST":
        if "name" in payload and "dimensionName" not in payload:
            payload["dimensionName"] = payload.pop("name")
    if "/accountingDimensionValue" in path and method == "POST":
        if "name" in payload and "displayName" not in payload:
            payload["displayName"] = payload.pop("name")

    return payload
```

### Error recovery in tool functions

```python
async def tripletex_post(ctx, path, body):
    result = await client.call("POST", path, json=body)
    if result["status"] >= 400:
        error_msg = str(result["data"])

        # Entity already exists → tell LLM to GET instead
        if "allerede" in error_msg or "i bruk" in error_msg:
            return f"Entity already exists. Use GET {path} to find it instead of POST."

        # No employment record → create one and retry
        if "arbeidsforhold" in error_msg and "/salary" in path:
            emp_id = extract_employee_id(body)
            if emp_id:
                await create_employment(client, emp_id)
                result = await client.call("POST", path, json=body)
                if result["status"] < 400:
                    return format_response(result)

        # Bank account missing → register and tell LLM to retry
        if "bankkontonummer" in error_msg:
            await register_bank_account(client)
            return "Bank account was missing. Registered now. Please retry."

    return format_response(result)
```

---

## 3. DATA PIPELINE

### Step 1: Download the OpenAPI spec

```bash
curl -o openapi.json https://<sandbox-url>/v2-docs/swagger.json
```

This is the single source of truth for all endpoints, field names, types, required flags, and enum values.

### Step 2: Generate an endpoint index for the LLM

From the OpenAPI spec, create a markdown table the LLM reads as part of its system prompt:
```
| Method | Path | Description |
| POST | /customer | Create customer |
| GET | /employee | Find employees |
...
```

**CRITICAL: Filter OUT all `[BETA]` endpoints.** They return 403 in the competition sandbox. We confirmed this — 0 BETA endpoints should be in the index.

### Step 3: Generate request body schemas (registry)

A JSON file mapping each endpoint to its request body schema. Used for local validation before sending — catches wrong field names and types without wasting API calls.

### Step 4: Build the HTTP client

```python
class TripletexClient:
    def __init__(self, base_url, session_token):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            auth=("0", session_token),  # Basic auth, username is always "0"
            timeout=30.0,
        )
        self.call_count = 0
        self.error_count = 0

    async def call(self, method, path, json=None, params=None):
        self.call_count += 1
        response = await self.client.request(method, f"/v2{path}", json=json, params=params)
        if response.status_code >= 400:
            self.error_count += 1
        return {"status": response.status_code, "data": response.json()}
```

### Step 5: Local payload validation

Before any POST/PUT goes to the API, validate against the registry schema. This catches wrong field names, wrong types, missing required fields — locally, without burning an API call.

---

## 4. NORWEGIAN ACCOUNTING DOMAIN KNOWLEDGE

### VAT rates and type IDs

**Outgoing VAT (sales — on products):**
| Rate | Description | vatType ID |
|------|------------|-----------|
| 25% | Standard (høy sats) | 3 |
| 15% | Food (middels sats, næringsmiddel) | 31 |
| 12% | Transport (lav sats) | 32 |
| 0% | Exempt (ingen avgift) | 5 |

**Incoming VAT (purchases — on supplier invoices):**
| Rate | Description | vatType ID |
|------|------------|-----------|
| 25% | Fradrag inngående avgift, høy sats | 1 |
| 15% | Fradrag inngående avgift, middels sats | 11 |

**WARNING**: These IDs work on MOST sandboxes but not ALL. If you get `"Ugyldig mva-kode"`, query `GET /ledger/vatType` and search for the correct type.

### Chart of accounts
| Number | Name | Use |
|--------|------|-----|
| 1920 | Bank | Bank account |
| 2400 | Leverandørgjeld | Accounts payable (supplier liability) |
| 2700 | Lønnsgjeld | Salary payable |
| 2710 | Inngående MVA høy sats | Input VAT 25% |
| 2711 | Inngående MVA middels sats | Input VAT 15% |
| 4000 | Varekostnad | Cost of goods |
| 5000 | Lønn | Salary expense |
| 6300 | Leie | Rent |
| 6340 | Lys/varme | Utilities |
| 6500 | Kontorkostnader | Office costs |
| 6860 | Kontorrekvisita | Office supplies |
| 7000 | Reisekostnader | Travel costs |
| 7100 | Bilkostnader | Car costs |
| 7140 | Reise og diett | Travel & per diem |
| 7300 | Markedsføring | Marketing |

### Key workflows

**Invoice creation**: Customer → Product(s) → Order (with orderLines) → PUT /order/{id}/:invoice

**Supplier invoice**: Supplier → Lookup accounts → POST /ledger/voucher with balanced postings

**Salary**: Employee → Salary types → POST /salary/transaction (or voucher fallback)

---

## 5. COMPLETE TASK-BY-TASK REFERENCE

### Task 1: Create Employee
**Scoring**: Employee found (2 pts), firstName (1), lastName (1), email (1), **admin role (5)**. Total: 10 pts.

**The admin role is 50% of the score!** You MUST call:
```
PUT /employee/entitlement/:grantEntitlementsByTemplate
  params: employeeId=<id>&template=ALL_PRIVILEGES
```

**Required fields the schema doesn't mark as required:**
- `department` — ALWAYS required. `GET /department` first, use first result's ID
- `userType` — required, use `"STANDARD"`
- `dateOfBirth` — format `"YYYY-MM-DD"`

**If prompt gives a start date**, create employment AFTER the employee:
```
POST /employee/employment
  {"employee": {"id": <id>}, "startDate": "YYYY-MM-DD",
   "employmentDetails": [{"date": "<startDate>", "employmentType": "ORDINARY"}]}
```

**Optimal**: 3-4 calls.

### Task 2: Create Customer
**Scored**: `name`, `organizationNumber`, `email`, address.

**Address must be on BOTH `postalAddress` AND `physicalAddress`.**

**`isCustomer: true`** is critical — without it, entity isn't marked as customer.

**Optimal**: 1 call.

### Task 3: Register Supplier
Same as customer but `isSupplier: true`.
**Optimal**: 1 call.

### Task 4: Create Product
**Scored**: `name`, `number` (STRING, not int), `priceExcludingVatCurrency`, `vatType`.

Must set both `priceExcludingVatCurrency` AND `priceIncludingVatCurrency`.

**Optimal**: 1 call (or 2 if VAT type lookup needed).

### Task 5: Create Departments
**`departmentNumber`** is required and must be unique.
**Optimal**: N calls for N departments (typically 3).

### Task 6: Multi-Line Invoice (3 products, mixed VAT)
1. `GET /customer?organizationNumber=xxx`
2. `POST /product` × 3
3. `POST /order` with orderLines — **NO vatType on order lines** (inherited from product)
4. `PUT /order/{id}/:invoice?invoiceDate=<today>`

**CRITICAL: vatType on order lines causes cascading errors.** Strip it.

**Optimal**: 6 calls.

### Task 7: Order → Invoice → Payment
1. `GET /customer?organizationNumber=xxx`
2. `POST /product` × N
3. `POST /order` (NO vatType on lines)
4. `PUT /order/{id}/:invoice?invoiceDate=<today>`
5. `GET /invoice/paymentType`
6. `PUT /invoice/{id}/:payment?paymentDate=<today>&paymentTypeId=<id>&paidAmount=<amount_incl_vat>`

**`paidAmount` MUST be total INCLUDING VAT** — get from invoice response's `amount` field.

**Optimal**: ~7 calls.

### Task 8: Register Payment on Existing Invoice
1. `GET /customer?organizationNumber=xxx`
2. `GET /invoice?customerId=<id>&invoiceDateFrom=2020-01-01&invoiceDateTo=2030-01-01`
3. `GET /invoice/paymentType`
4. `PUT /invoice/{id}/:payment?paymentDate=<today>&paymentTypeId=<id>&paidAmount=<amount_incl_vat>`

**`invoiceDateFrom` and `invoiceDateTo` are REQUIRED** on GET /invoice.

**Optimal**: 4 calls.

### Task 9: Payment Reversal
Same as Task 8 but with **negative** `paidAmount`.
**Optimal**: 4 calls.

### Task 10: Credit Note
1. `GET /customer?organizationNumber=xxx`
2. `GET /invoice?customerId=<id>&invoiceDateFrom=2020-01-01&invoiceDateTo=2030-01-01`
3. `PUT /invoice/{id}/:createCreditNote?date=<today>`

**Optimal**: 3 calls.

### Task 11: Create Project
1. `GET /customer?organizationNumber=xxx`
2. `GET /employee?email=xxx`
3. `POST /project` with `name`, `number` (unique!), `startDate`, `projectManager`, `customer`

**Customer and employee already exist** — use GET, not POST.

**Optimal**: 3 calls.

### Task 12: Fixed-Price Project + Milestone Invoice
1. `GET /customer`, `GET /employee`
2. `POST /project` with `isFixedPrice: true`, `fixedprice: <amount>`
3. `POST /product` for milestone
4. `POST /order` with amount = fixedprice × percentage
5. `PUT /order/{id}/:invoice`

**Optimal**: 6 calls.

### Task 13: Hourly Billing (Timesheet + Project Invoice)
1. `GET /customer`, `GET /employee` — **NEVER POST these, they exist**
2. `POST /project`
3. `GET /activity?name=xxx` — if not found, `POST /activity` with `activityType: "PROJECT_GENERAL_ACTIVITY"`
4. `POST /project/projectActivity` — link activity to project
5. `POST /timesheet/entry` — date MUST be >= project startDate
6. `POST /product`, `POST /order`, `PUT /order/{id}/:invoice`

**Optimal**: ~9 calls.

### Task 14: Salary / Payroll
1. `GET /employee?email=xxx`
2. `GET /salary/type?name=Fastlønn` and `GET /salary/type?name=Bonus`
3. `POST /salary/transaction`:
```json
{
  "date": "2026-03-31", "year": 2026, "month": 3,
  "payslips": [{
    "employee": {"id": <id>},
    "date": "2026-03-31", "year": 2026, "month": 3,
    "specifications": [
      {"salaryType": {"id": <base>}, "rate": 45000, "count": 1},
      {"salaryType": {"id": <bonus>}, "rate": 10000, "count": 1}
    ]
  }]
}
```

**Use `rate`, NOT `amount`** — amount is auto-calculated as rate × count.

**date/year/month MUST be on BOTH transaction AND each payslip.**

**If "arbeidsforhold" error**: Create employment first via `POST /employee/employment`, then retry. If still fails, fall back to manual voucher (debit 5000, credit 2700).

**Optimal**: 4 calls (or 6 with employment creation).

### Task 15: Travel Expense
1. `GET /employee?email=xxx`
2. `POST /travelExpense` with `travelDetails` INLINE (not just costs)
3. `GET /travelExpense/rateCategory`, `GET /travelExpense/rate`
4. `POST /travelExpense/perDiemCompensation`
5. `GET /travelExpense/paymentType`, `GET /currency?code=NOK`
6. `POST /travelExpense/cost` × N

**`travelDetails` must be INLINE** — without it, creates wrong expense type.
**Costs are SEPARATE POST calls**, not inline.
**Do NOT include `countryCode`** — causes "Country not found" error.

**Optimal**: ~9 calls.

### Task 16: Accounting Dimensions + Voucher
1. `POST /ledger/accountingDimensionName` — use `dimensionName` NOT `name`
2. `POST /ledger/accountingDimensionValue` × N — use `displayName` NOT `name`, include `dimensionIndex` from step 1
3. `GET /ledger/voucherType`, `GET /ledger/account?number=<expense>`, `GET /ledger/account?number=1920`
4. `POST /ledger/voucher` — match `freeAccountingDimensionN` to `dimensionIndex`

**Optimal**: ~8 calls.

### Task 17: Create + Send Invoice
1. `GET /customer`, `POST /product`, `POST /order`
2. `PUT /order/{id}/:invoice?invoiceDate=<today>`
3. `PUT /invoice/{id}/:send?sendType=EMAIL`

**Product does NOT pre-exist** (must create). Customer DOES pre-exist.

**Optimal**: 5 calls.

### Task 18: Supplier Invoice via Voucher
**POST /supplierInvoice does NOT exist!** Use `POST /ledger/voucher`.

1. `GET /supplier?organizationNumber=xxx` (or POST if new)
2. `GET /ledger/account?number=<expense>`, `GET /ledger/account?number=2400`
3. `GET /ledger/voucherType`
4. `POST /ledger/voucher`:

**For 21100 NOK incl 25% VAT:**
- Net = 21100 / 1.25 = 16880
- VAT = 21100 - 16880 = 4220

**2-posting approach (let Tripletex auto-calculate VAT):**
```json
{"postings": [
  {"account": {"id": <expense>}, "amountGross": 16880, "amountGrossCurrency": 16880,
   "vatType": {"id": 1}, "row": 1},
  {"account": {"id": <2400>}, "amountGross": -21100, "amountGrossCurrency": -21100,
   "supplier": {"id": <id>}, "row": 2}
]}
```

**If that fails, use 3 explicit postings:**
```json
{"postings": [
  {"account": {"id": <expense>}, "amountGross": 16880, "amountGrossCurrency": 16880, "row": 1},
  {"account": {"id": <2710>}, "amountGross": 4220, "amountGrossCurrency": 4220, "row": 2},
  {"account": {"id": <2400>}, "amountGross": -21100, "amountGrossCurrency": -21100,
   "supplier": {"id": <id>}, "row": 3}
]}
```

**Optimal**: 4-5 calls.

### Task 19 (Tier 3): Employee from PDF
PDF offer letter → extract with LLM vision → create employee (same as Task 1).
**Optimal**: 3-4 calls + 1 vision call.

### Task 20 (Tier 3): Bank Reconciliation from CSV
Parse CSV → match transactions to invoices → register payments.
**Optimal**: varies.

### Task 21 (Tier 3): Ledger Error Correction
GET vouchers for Jan/Feb → find errors → create correction vouchers.
**Error types**: wrong account, duplicate voucher, missing VAT line, incorrect amount.
**Optimal**: varies.

---

## 6. LAZY SETUP (only when needed)

Every submission gets a fresh sandbox, but NOT every task needs setup. Running setup on every task wastes API calls and hurts efficiency on simple tasks.

### Bank account registration
Only needed for invoice/payment tasks. Trigger lazily:
```python
if "/:invoice" in path or "/:payment" in path:
    await ensure_bank_account(client)
    # GET /ledger/account?number=1920 → PUT with bankAccountNumber="12345678903"
```

### Employment creation
Only needed for salary tasks. Trigger on "arbeidsforhold" error:
```python
if "arbeidsforhold" in error_msg:
    await create_employment(client, employee_id)
    # POST /employee/employment with startDate, ORDINARY, PERMANENT, MONTHLY_WAGE
```

---

## 7. CRITICAL RULES (from production failures)

### Action endpoints use QUERY PARAMS, not body
- `PUT /order/{id}/:invoice` → params: `invoiceDate`
- `PUT /invoice/{id}/:payment` → params: `paymentDate`, `paymentTypeId`, `paidAmount`
- `PUT /invoice/{id}/:createCreditNote` → params: `date`
- `PUT /invoice/{id}/:send` → params: `sendType`
- `PUT /employee/entitlement/:grantEntitlementsByTemplate` → params: `employeeId`, `template`

### Entities: GET existing, POST new
- Customers, employees, suppliers mentioned in context → they ALREADY EXIST → use GET
- Products for orders → usually need to be CREATED → use POST
- If POST fails with "allerede"/"already exists" → switch to GET

### Voucher posting rules
1. **Rows start at 1** — row 0 is system-reserved, causes instant 422
2. **Use `amountGross` and `amountGrossCurrency`** — not `amount`
3. **Postings must balance** — sum of amountGross = 0
4. **Positive = debit, negative = credit**
5. **Supplier ref goes on the AP (2400) posting**

### GET /invoice requires date range
Always pass `invoiceDateFrom=2020-01-01&invoiceDateTo=2030-01-01`.

### GET /ledger/account uses `number` param
NOT `numberFrom`/`numberTo` — those filter by internal ID range.

### Dates
Always `YYYY-MM-DD`. Parse natural language dates from prompts.

### Linked entities
Always `{"id": <int>}`. Never send the full object.

### Order `deliveryDate`
Required. If not in task, default to same as `orderDate`.

---

## 8. ERROR REFERENCE (all from production)

### Voucher errors
| Error | Cause | Fix |
|-------|-------|-----|
| `Posteringene på rad 0 (guiRow 0) er systemgenererte` | row: 0 | Rows must start at 1 |
| `Et bilag kan ikke registreres uten posteringer` | Postings empty or filtered | Ensure postings have account + amountGross |
| `amountGross` missing | Used `amount` | Use `amountGross` and `amountGrossCurrency` |
| Postings don't balance | Sum != 0 | Verify: debits + credits = 0 |

### Invoice errors
| Error | Cause | Fix |
|-------|-------|-----|
| `bankkontonummer` | No bank account on 1920 | PUT /ledger/account with bankAccountNumber |
| `deliveryDate: Kan ikke være null` | Missing deliveryDate | Default to orderDate or TODAY |
| `invoiceDateFrom: Kan ikke være null` | GET /invoice without date range | Always include date range params |
| paidAmount wrong (partial score) | Used ex-VAT amount | Get total from invoice response |

### Employee/salary errors
| Error | Cause | Fix |
|-------|-------|-----|
| `arbeidsforhold i perioden` | No employment record | POST /employee/employment first |
| `allerede en bruker med denne e-postadressen` | POST existing employee | Use GET first |
| Salary date/year/month null | Missing at payslip level | Set on BOTH transaction AND payslip |
| `rate: Kan ikke være null` | Used `amount` instead of `rate` | Always use `rate` on salary specs |

### Timesheet errors
| Error | Cause | Fix |
|-------|-------|-----|
| `kan ikke registreres timer før denne datoen` | Date before project startDate | Use date >= project startDate |
| `activityType PROJECT_SPECIFIC not valid` | Wrong enum | Use `PROJECT_GENERAL_ACTIVITY` or `PROJECT_SPECIFIC_ACTIVITY` |

### General errors
| Error | Cause | Fix |
|-------|-------|-----|
| BETA endpoint 403 | Used [BETA] endpoint | Filter BETA from endpoint index |
| 120s Cloudflare timeout | Agent too slow | Budget 110s |
| `POST /supplierInvoice` 404 | Endpoint doesn't exist | Use POST /ledger/voucher |
| `Ugyldig mva-kode` | Wrong VAT type ID | Query GET /ledger/vatType to find correct one |

---

## 9. SYSTEM PROMPT FOR THE LLM

The system prompt should contain:
1. Today's date
2. Available endpoints (the filtered index from the OpenAPI spec)
3. Norwegian accounting knowledge (from Section 4 above)
4. Task-specific workflow guides (from Section 5 above)
5. Rules about GET vs POST, action endpoints, etc. (from Section 7 above)

**The system prompt tells the LLM WHAT to do. The tool functions handle HOW (apply_fixes, validation, error recovery).**

Keep the system prompt focused and not too long — the LLM needs room for tool call context.

---

## 10. FILE HANDLING (Tier 3)

### PDFs
Pass as base64 vision input to the LLM. Gemini 3.1 Pro has strong vision.

### CSVs
Parse in Python code. Give the LLM a summary of transactions.

### Implementation
```python
async def handle_files(files):
    processed = []
    for f in files:
        if f["name"].endswith(".pdf"):
            processed.append({"type": "image", "data": f["content"]})  # base64
        elif f["name"].endswith(".csv"):
            rows = parse_csv(base64.b64decode(f["content"]))
            processed.append({"type": "text", "data": format_csv_summary(rows)})
    return processed
```

---

## 11. TESTING STRATEGY

### Before every deploy
1. All Python files parse: `python -c "import agent; import api"`
2. Server starts: `curl localhost:8080/health`
3. Test at least the 3 hardest tasks (supplier invoice, salary, timesheet+invoice) on sandbox
4. No task takes longer than 90 seconds
5. Zero 4xx errors on simple tasks

### Test cases to build
Write test prompts for all 30 task types. For each:
1. Send the prompt to your agent
2. Verify the result via Tripletex API queries
3. Count API calls and errors
4. Track correctness per field

### Important sandbox note
Local sandbox is PERSISTENT (not reset between tests). Competition sandboxes are FRESH. Test both:
- "Clean" tests: unique entity names to avoid collisions
- "Collision" tests: verify "already exists" is handled gracefully

---

## 12. DEPLOYMENT

### Stack
- Docker container → Google Cloud Run
- Health check endpoint: `GET /health` → `{"status": "ok"}`
- Main endpoint: `POST /solve`
- File: `deploy.sh` handles deployment (DO NOT remove this file)

### Submission strategy
- 3 concurrent submissions (verified teams)
- 10 per task per day
- Don't waste submissions on tasks that already score well
- Focus on zero-score tasks first
- When Tier 3 opens: prioritize immediately (6 points each)
- Never deploy untested changes

---

## 13. WHAT TO BUILD (in order)

1. **HTTP client** — authenticated, with call counting
2. **Data pipeline** — OpenAPI spec → endpoint index + schema registry (filter BETA)
3. **Payload validator** — validate against registry before sending
4. **apply_fixes function** — all the silent corrections from Section 2
5. **Tool functions** — tripletex_get, tripletex_post, tripletex_put with apply_fixes + validation + error recovery
6. **System prompt** — accounting knowledge + workflow guides + rules
7. **File handler** — PDF vision + CSV parsing
8. **Agent orchestrator** — OpenAI Agents SDK with tool-calling loop
9. **API server** — FastAPI with /health and /solve
10. **Test suite** — at least the 3 hardest tasks on sandbox
11. **Dockerfile + deploy.sh**

---

## 14. OPEN QUESTIONS FOR YOU

These are things we're not 100% sure about. If you have better ideas, please suggest them:

1. **Architecture**: We're recommending tool-calling over plan-then-execute. But the teammate's strategy doc also suggests a hybrid: LLM classifies + extracts data in ONE call, then deterministic code executes the workflow. This would be faster (1 LLM call vs many) but less flexible. What do you think?

2. **VAT type IDs**: We hardcode them but they might vary per sandbox. Should we always query `GET /ledger/vatType` first, or is the hardcoded fallback sufficient?

3. **Supplier invoice**: 2-posting approach (with vatType on expense posting to auto-generate VAT) vs 3-posting approach (explicit VAT posting). Which is more reliable? We've seen conflicting results.

4. **Efficiency**: For simple tasks (create customer = 1 API call), the tool-calling approach might be overkill (LLM overhead). Should we have a fast path for trivial tasks?

5. Is thing too hardocded now? should the LLM understand it self instead so we do not lose API calls? like feel the banking part where we to the lazy thing and all the apply_fixes functions. do you have any better solutions that allows the agent to do the correct things without being hardcoded fixes. 

**Remember**: If you need me to do something (download a file, check API docs, run a command), just tell me step by step and I'll do it. Let's win this!
