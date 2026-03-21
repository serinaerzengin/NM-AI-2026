# V4 Analysis — Successful Runs (Efficiency Optimization)

**Goal**: Reduce API calls on runs that already complete successfully to maximize efficiency bonus.
**Deployment**: Revision 00041, 2026-03-21 ~18:50 UTC
**Total successful runs**: 22

## Important Context
- Each task has 56 variants (7 languages × 8 data sets). Fixes must be GENERAL patterns.
- Efficiency bonus only applies when correctness = 1.0. Fewer API calls + zero errors = up to 2x score.
- Context investigation confirmed: the LLM conversation history persists correctly across all iterations.
  Messages grow from 2 → 38+, all tool results stay in context, total chars grow from 15K → 87K+.
  The LLM is NOT losing context between calls.

## Root Cause of Excessive API Calls

### Finding: LLM probes for account numbers it doesn't know
Verified on a monthly closing task (24 calls, 0 errors, 88s):
- The LLM needed the depreciation accumulation account
- It searched: 1209, 1239, 1249, 1149, 1230, 1240, 1250, 1140, 1241, 1231, 1201, 1290
- **12 GET calls just guessing account numbers** — each for a DIFFERENT account
- The context had all previous responses, but the LLM didn't know which number to use

### Root causes:
1. **Domain knowledge gap**: System prompt only lists ~15 common accounts. The LLM doesn't know the
   Norwegian chart of accounts structure (e.g. 1200=asset → 1209=accumulated depreciation)
2. **No batch lookup**: The LLM could GET /ledger/account?count=1000 once to see ALL accounts,
   but instead probes one at a time
3. **Verification GETs**: After creating vouchers, the LLM re-fetches balance sheet and postings
   to "verify" — wasting 2-5 calls per task
4. **Duplicate GETs**: Same endpoint called multiple times with same params across iterations

---

## Run-by-Run Efficiency Analysis

### 5fcc4052 — 1 calls (optimal ~1, saving 0)
**Prompt**: Crea el cliente Solmar SL con número de organización 879505631. La dirección es Parkveien 49, 4611 Kristiansand. Correo:
**Breakdown**: GET:0(unique)/0(total) POST:1 PUT:0
**GET paths**: 
**POST paths**: /customer

### 02429449 — 1 calls (optimal ~1, saving 0)
**Prompt**: Opprett kunden Skogheim AS med organisasjonsnummer 893718729. Adressa er Storgata 111, 7010 Trondheim. E-post: post@skog
**Breakdown**: GET:0(unique)/0(total) POST:1 PUT:0
**GET paths**: 
**POST paths**: ?

### 09e3faa4 — 2 calls (optimal ~2, saving 0)
**Prompt**: Create three departments in Tripletex: "Kundeservice", "Økonomi", and "Drift".
**Breakdown**: GET:1(unique)/1(total) POST:1 PUT:0
**GET paths**: /department
**POST paths**: /department/list

### eecd67bb — 3 calls (optimal ~3, saving 0)
**Prompt**: Crea el proyecto "Análisis Costa" vinculado al cliente Costa Brava SL (org. nº 921937946). El director del proyecto es I
**Breakdown**: GET:2(unique)/2(total) POST:1 PUT:0
**GET paths**: /customer, /employee
**POST paths**: /project

### f6649e02 — 3 calls (optimal ~3, saving 0)
**Prompt**: Créez le projet "Intégration Montagne" lié au client Montagne SARL (nº org. 975615766). Le chef de projet est Jules Robe
**Breakdown**: GET:2(unique)/2(total) POST:1 PUT:0
**GET paths**: /customer, /employee
**POST paths**: /project

### 02e6e2e9 — 3 calls (optimal ~3, saving 0)
**Prompt**: Nous avons un nouvel employé nommé Jules Richard, né le 2. August 1986. Veuillez le créer en tant qu'employé avec l'e-ma
**Breakdown**: GET:1(unique)/1(total) POST:2 PUT:0
**GET paths**: /department
**POST paths**: ?, /employee/employment

### 4b4e3d28 — 4 calls (optimal ~4, saving 0)
**Prompt**: O pagamento de Luz do Sol Lda (org. nº 856642402) referente à fatura "Horas de consultoria" (9000 NOK sem IVA) foi devol
**Breakdown**: GET:3(unique)/3(total) POST:0 PUT:1
**GET paths**: /customer, /invoice, /invoice/paymentType
**POST paths**: 
**PUT paths**: /invoice/2147568191/:payment

### 12716714 — 5 calls (optimal ~4, saving 1)
**Prompt**: The customer Greenfield Ltd (org no. 853801941) has an outstanding invoice for 34450 NOK excluding VAT for "Consulting H
**Breakdown**: GET:3(unique)/3(total) POST:0 PUT:1
**GET paths**: /customer, /invoice, /invoice/paymentType
**POST paths**: 
**PUT paths**: /invoice/2147569757/:payment

### ad5dcccd — 6 calls (optimal ~6, saving 0)
**Prompt**: Du har mottatt et tilbudsbrev (se vedlagt PDF) for en ny ansatt. Utfor komplett onboarding: opprett den ansatte, tilknyt
**Breakdown**: GET:1(unique)/1(total) POST:4 PUT:1
**GET paths**: /department
**POST paths**: /department, /employee, /employee/employment, /employee/employment/details
**PUT paths**: /employee/employment/details/3726899

### 0fee50b5 — 6 calls (optimal ~5, saving 1)
**Prompt**: Wir haben die Rechnung INV-2026-6337 vom Lieferanten Waldstein GmbH (Org.-Nr. 927720523) über 55950 NOK einschließlich M
**Breakdown**: GET:4(unique)/5(total) POST:1 PUT:0
**Duplicate GETs**: /ledger/account(×2)
**GET paths**: /supplier, /ledger/voucherType, /ledger/vatType, /ledger/account, /ledger/account
**POST paths**: /ledger/voucher

### 6c193d05 — 7 calls (optimal ~6, saving 1)
**Prompt**: Defina um preço fixo de 240750 NOK no projeto "Desenvolvimento e-commerce" para Cascata Lda (org. nº 908648579). O gesto
**Breakdown**: GET:2(unique)/2(total) POST:3 PUT:1
**GET paths**: /customer, /employee
**POST paths**: ?, /product, /order
**PUT paths**: /order/402028691/:invoice

### 0fc920c4 — 7 calls (optimal ~6, saving 1)
**Prompt**: Has recibido una factura de proveedor (ver PDF adjunto). Registra la factura en Tripletex. Crea el proveedor si no exist
**Breakdown**: GET:4(unique)/5(total) POST:2 PUT:0
**Duplicate GETs**: /ledger/account(×2)
**GET paths**: /supplier, /ledger/voucherType, /ledger/account, /ledger/vatType, /ledger/account
**POST paths**: /supplier, /ledger/voucher

### 7ae16a0c — 8 calls (optimal ~6, saving 2)
**Prompt**: Crea un pedido para el cliente Luna SL (org. nº 966920963) con los productos Desarrollo de sistemas (5271) a 6950 NOK y 
**Breakdown**: GET:3(unique)/4(total) POST:1 PUT:2
**Duplicate GETs**: /product(×2)
**GET paths**: /customer, /product, /product, /invoice/paymentType
**POST paths**: ?
**PUT paths**: /order/402028763/:invoice, /invoice/2147626585/:payment

### c2ef3465 — 8 calls (optimal ~6, saving 2)
**Prompt**: Du har motteke ein leverandorfaktura (sjaa vedlagt PDF). Registrer fakturaen i Tripletex. Opprett leverandoren viss den 
**Breakdown**: GET:4(unique)/6(total) POST:2 PUT:0
**Duplicate GETs**: /ledger/account(×3)
**GET paths**: /supplier, /ledger/voucherType, /ledger/vatType, /ledger/account, /ledger/account, /ledger/account
**POST paths**: ?, /ledger/voucher

### 55b7083b — 8 calls (optimal ~8, saving 0)
**Prompt**: Du har motteke eit tilbodsbrev (sjaa vedlagt PDF) for ein ny tilsett. Utfor komplett onboarding: opprett den tilsette, t
**Breakdown**: GET:2(unique)/2(total) POST:5 PUT:1
**GET paths**: /department, /division
**POST paths**: /department, /employee, ?, /employee/employment, /employee/employment/details
**PUT paths**: ?

### 75980176 — 10 calls (optimal ~5, saving 5)
**Prompt**: Vi trenger Whiteboard fra denne kvitteringen bokfort pa avdeling HR. Bruk riktig utgiftskonto basert pa kjopet, og sorg 
**Breakdown**: GET:4(unique)/9(total) POST:1 PUT:0
**Duplicate GETs**: /ledger/account(×6)
**GET paths**: /department, /ledger/voucherType, /ledger/vatType, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account
**POST paths**: /ledger/voucher

### a5922aa1 — 12 calls (optimal ~10, saving 2)
**Prompt**: We sent an invoice for 14988 EUR to Northwave Ltd (org no. 972362980) when the exchange rate was 11.80 NOK/EUR. The cust
**Breakdown**: GET:8(unique)/9(total) POST:1 PUT:1
**Duplicate GETs**: /ledger/account(×2)
**GET paths**: /customer, /invoice/paymentType, /ledger/voucherType, /ledger/account, /ledger/account, /invoice, /currency, /invoice/2147626830, /order/orderline/1607567383
**POST paths**: /ledger/voucher
**PUT paths**: /invoice/2147626830/:payment

### 66801567 — 19 calls (optimal ~11, saving 8)
**Prompt**: Realize o encerramento anual simplificado de 2025: 1) Calcule e registe a depreciação anual de três ativos: Kontormaskin
**Breakdown**: GET:4(unique)/12(total) POST:7 PUT:0
**Duplicate GETs**: /ledger/posting(×2), /ledger/account(×7), /balanceSheet(×2)
**GET paths**: /ledger/voucherType, /ledger/posting, /ledger/account, /ledger/posting, /balanceSheet, /ledger/account, /ledger/account, /ledger/account, /balanceSheet, /ledger/account, /ledger/account, /ledger/account
**POST paths**: /ledger/account, /ledger/account, /ledger/voucher, ?, /ledger/voucher, /ledger/voucher, ?

### 349b6e77 — 20 calls (optimal ~17, saving 3)
**Prompt**: Totalkostnadene auka monaleg frå januar til februar 2026. Analyser hovudboka og finn dei tre kostnadskontoane med størst
**Breakdown**: GET:5(unique)/8(total) POST:12 PUT:0
**Duplicate GETs**: /balanceSheet(×2), /ledger/account(×3)
**GET paths**: /ledger/posting, /balanceSheet, /balanceSheet, /ledger/account, /ledger/account, /ledger/account, /employee, /activity
**POST paths**: /project, /project, /project, /project/projectActivity, /project/projectActivity, /project/projectActivity, /activity, /activity, /activity, /project/projectActivity, /project/projectActivity, /project/projectActivity

### e74f2ebb — 21 calls (optimal ~10, saving 11)
**Prompt**: Realice el cierre anual simplificado de 2025: 1) Calcule y contabilice la depreciación anual de tres activos: Kontormask
**Breakdown**: GET:4(unique)/15(total) POST:6 PUT:0
**Duplicate GETs**: /ledger/account(×12)
**GET paths**: /ledger/voucherType, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/posting, /balanceSheet, /ledger/account, /ledger/account, /ledger/account
**POST paths**: ?, /ledger/voucher, /ledger/voucher, /ledger/voucher, ?, ?

### 3eb0feb1 — 22 calls (optimal ~6, saving 16)
**Prompt**: Realize o encerramento mensal de março de 2026. Registe a reversão de acréscimos (9000 NOK por mês da conta 1700 para de
**Breakdown**: GET:4(unique)/20(total) POST:2 PUT:0
**Duplicate GETs**: /ledger/account(×15), /ledger/posting(×3)
**GET paths**: /ledger/voucherType, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /balanceSheet, /ledger/posting, /ledger/posting, /ledger/posting
**POST paths**: /ledger/account, /ledger/voucher

### 98757578 — 40 calls (optimal ~6, saving 34)
**Prompt**: Perform month-end closing for March 2026. Post accrual reversal (14550 NOK per month from account 1720 to expense). Reco
**Breakdown**: GET:5(unique)/39(total) POST:1 PUT:0
**Duplicate GETs**: /ledger/voucherType(×2), /ledger/account(×26), /ledger/posting(×8), /balanceSheet(×2)
**Trailing verification GETs**: 1 after last write
**GET paths**: /ledger/voucherType, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/posting, /ledger/posting, /balanceSheet, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/account, /ledger/openPost, /ledger/posting, /ledger/posting, /ledger/posting, /ledger/posting, /ledger/posting, /ledger/voucherType, /ledger/posting, /balanceSheet
**POST paths**: ?

---

## Waste Patterns Summary

| Pattern | Runs affected | Total calls wasted |
|---------|--------------|-------------------|
| Duplicate GET /ledger/account | 10 runs | ~68 calls |
| Duplicate GET /ledger/posting | 3 runs | varies |
| Duplicate GET /balanceSheet | 3 runs | varies |
| Trailing verification GETs | 1 runs | 1 calls |
| **Total potential saving** | **22 runs** | **~87 calls** |

## Suggested Fixes (ordered by impact)

### 1. Batch account lookup (HIGH — saves ~50 calls across all runs)
Add to system prompt: "When you need multiple account IDs, GET /ledger/account?count=1000 once
to see all accounts, then use IDs from the response. Do NOT look up accounts one at a time."
Add POST /ledger/account/list to endpoint table for batch creation.

### 2. Expand chart of accounts in system prompt (HIGH — prevents probing)
The current chart lists ~15 accounts. Add the full structure including:
- 1200-1290: Fixed assets and accumulated depreciation (1200→1209, 1210→1219, etc.)
- 1700: Prepaid expenses
- 2900/2920/2990: Accrued liabilities
- 6010/6020/6030: Depreciation expense accounts
- 8060/8160: Agio/disagio
This prevents the LLM from probing 12 accounts to find the right depreciation account.

### 3. Stronger no-verification rule (MEDIUM — saves ~10 calls)
Current rule #10 says don't verify. But the LLM still does 2-5 verification GETs after writes.
Make it more explicit: "After POST/PUT succeeds, do NOT call GET on the same resource or related
balance sheet. The task is done — move to the next step or finish."

### 4. Add batch endpoints to system prompt (MEDIUM — efficiency on multi-item tasks)
Available non-BETA batch endpoints: POST /product/list, POST /department/list,
POST /employee/list, POST /ledger/account/list, POST /ledger/voucher/list,
POST /timesheet/entry/list, POST /order/orderline/list, POST /supplier/list.
Note: 09e3faa4 already used POST /department/list successfully (2 calls for 3 depts).
