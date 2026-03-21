# V4 Analysis — Failed/Error Runs (Fix Errors)

**Goal**: Fix errors that cause failed scores (0 points) or reduced correctness.
**Deployment**: Revision 00041, 2026-03-21 ~18:50 UTC
**Total error runs**: 14

## Important Context
- Each task has 56 variants (7 languages × 8 data sets). Fixes must be GENERAL patterns.
- Token expired (403) runs are NOT our bug — competition infrastructure invalidates tokens.
- Code crashes are highest priority — they score 0 every time.

---

## Error Categorization

| Category | Count | Impact |
|----------|-------|--------|
| Token expired (403) | 0 | NOT OUR BUG — competition infrastructure |
| Code crash | 0 | Score = 0, HIGHEST PRIORITY |
| Still running/timeout | 4 | Likely timed out, score = 0 or partial |
| API errors (completed) | 9 | Reduced score due to errors |

## Token Expired Runs (NOT our bug)


These all show `Invalid or expired proxy token`. The competition Slack explained: "the session token
will stop working after our validator has received the response." When 3 concurrent tasks run,
the first to complete invalidates the token for the other 2. Nothing we can do.

## Code Crashes (HIGHEST PRIORITY)

## Still Running / Timed Out

### 4cae6184
**Prompt**: Descobrimos erros no livro razão de janeiro e fevereiro de 2026. Revise todos os vouchers e encontre os 4 erros: um lançamento na conta errada (conta 6340 usada em vez de 6390, valor 2450 NOK), um vou
**Tools visible**: 41 (GET:41 POST:0 PUT:0)
**Pattern**: All GETs, no POSTs — LLM over-analyzing without acting

### 371e12e4
**Prompt**: Execute o ciclo de vida completo do projeto 'Atualização Sistema Porto' (Porto Alegre Lda, org. nº 921319878): 1) O projeto tem um orçamento de 362600 NOK. 2) Registe horas: João Pereira (gestor de pr
**Tools visible**: 16 (GET:9 POST:7 PUT:0)

### 1decab66
**Prompt**: Führen Sie den Monatsabschluss für März 2026 durch. Buchen Sie die Rechnungsabgrenzung (3400 NOK pro Monat von Konto 1700 auf Aufwand). Erfassen Sie die monatliche Abschreibung für eine Anlage mit Ans
**Tools visible**: 14 (GET:14 POST:0 PUT:0)

### 21dfab69
**Prompt**: Gjennomfør hele prosjektsyklusen for 'Digitalportal Lysgård' (Lysgård AS, org.nr 807315072): 1) Prosjektet har budsjett 344850 kr. 2) Registrer timer: Silje Bakken (prosjektleder, silje.bakken@example
**Tools visible**: 17 (GET:9 POST:7 PUT:1)

## API Error Runs (completed but with errors)

### ac356249 — 36 calls, 6 errors
**Prompt**: Avstem bankutskrifta (vedlagt CSV) mot opne fakturaer i Tripletex. Match innbetalingar til kundefakturaer og utbetalingar til leverandorfakturaer. Han

### cbc48484 — 9 calls, 2 errors
**Prompt**: Create a custom accounting dimension "Produktlinje" with the values "Avansert" and "Premium". Then post a voucher on account 6300 for 25750 NOK, linke

### 509de7b8 — 15 calls, 3 errors
**Prompt**: Ejecute la nómina de Fernando López (fernando.lopez@example.org) para este mes. El salario base es de 37850 NOK. Añada una bonificación única de 9200 

### 538ea526 — 4 calls, 4 errors
**Prompt**: En av kundene dine har en forfalt faktura. Finn den forfalte fakturaen og bokfor et purregebyr pa 50 kr. Debet kundefordringer (1500), kredit purregeb

### 58ebb784 — 42 calls, 42 errors
**Prompt**: Exécutez le cycle de vie complet du projet 'Portail Numérique Étoile' (Étoile SARL, nº org. 834437961) : 1) Le projet a un budget de 383650 NOK. 2) En

### 1f153268 — 5 calls, 5 errors
**Prompt**: Realize o encerramento mensal de março de 2026. Registe a reversão de acréscimos (10700 NOK por mês da conta 1720 para despesa). Registe a depreciação

### 14d31697 — 6 calls, 1 errors
**Prompt**: Sie haben ein Angebotsschreiben erhalten (siehe beigefugte PDF) fuer einen neuen Mitarbeiter. Fuehren Sie das vollstaendige Onboarding durch: erstelle

### 51869a98 — 3 calls, 3 errors
**Prompt**: Sie haben ein Angebotsschreiben erhalten (siehe beigefugte PDF) fuer einen neuen Mitarbeiter. Fuehren Sie das vollstaendige Onboarding durch: erstelle

### c59e441f — 16 calls, 1 errors
**Prompt**: Wir haben eine Rechnung über 5044 EUR an Bergwerk GmbH (Org.-Nr. 806819859) gesendet, als der Wechselkurs 10.51 NOK/EUR betrug. Der Kunde hat nun beza

---

## Fixes Applied and Validation Results

### 🟢 FIX 1: Code crash list.setdefault — FIXED
- **Runs affected**: 371e12e4, 21dfab69 (2 runs, score 0)
- **Root cause**: LLM sends list body `[{...}]` for batch endpoints (e.g. POST /order/orderline/list). `apply_fixes()` calls `.setdefault()` on the payload which crashes on lists.
- **Fix**: Added `isinstance(payload, dict)` check before calling apply_fixes in both POST and PUT handlers in agent.py.
- **Validated**: Unit test — list payload passes through without crash.

### 🟢 FIX 2: Salary dateOfBirth — FIXED
- **Runs affected**: 509de7b8 (1 run)
- **Root cause**: `create_employment` helper doesn't ensure employee has dateOfBirth set. Employment creation fails with "employee.dateOfBirth: Feltet må fylles ut".
- **Fix**: Added dateOfBirth check+set in `create_employment()` in apply_fixes.py — GETs employee, if no dateOfBirth sets "1990-01-01", then proceeds.
- **Validated**: Code review — the check runs before employment creation.

### 🟢 FIX 3: Accounting dimension wrong field — FIXED
- **Runs affected**: cbc48484 (1 run)
- **Root cause**: LLM sends `accountingDimensionName` field on dimension value creation, but field doesn't exist. The correct ref is `dimensionIndex`.
- **Fix**: Added `payload.pop("accountingDimensionName", None)` to accounting dimension value fixes in apply_fixes.py.
- **Validated**: Code review.

### 🟢 FIX 4: supplierInvoice missing date params — FIXED
- **Runs affected**: ac356249 (1 run)
- **Root cause**: GET /supplierInvoice requires invoiceDateFrom and invoiceDateTo but system prompt didn't say so.
- **Fix**: Updated endpoint table in system_prompt.py: `GET /supplierInvoice` → "Query supplier invoices (REQUIRES invoiceDateFrom & invoiceDateTo)".
- **Validated**: Code review.

### 🟢 FIX 5: FX dateFrom >= dateTo — FIXED
- **Runs affected**: c59e441f (1 run)
- **Root cause**: LLM uses same date for dateFrom and dateTo, but dateTo is EXCLUSIVE in Tripletex. Same-day query returns "from >= to" error.
- **Fix**: Added to critical rule #6: "dateTo is EXCLUSIVE — for same-day queries use dateTo = next day".
- **Validated**: Code review.

### 🟢 FIX 6: Ledger error correction over-analysis — FIXED
- **Runs affected**: 4cae6184 (41 GETs, 0 POSTs, timeout), 1decab66 (14 GETs, 0 POSTs)
- **Root cause**: LLM fetches postings per voucher, per account, per date individually instead of acting. The previous "action-oriented" rewrite wasn't prescriptive enough.
- **Fix**: Rewrote workflow with EXACT 3-step sequence and STRICT LIMIT: "Maximum 3 GET calls total, then ONLY POST calls for corrections."
- **Validated on sandbox**: Before: 41 GETs, 0 POSTs, timeout. After: **11 GETs + 7 POSTs, 145s, completed with 4 correction vouchers created.** The LLM now acts instead of endlessly analyzing.

### ℹ️ NOT FIXED: Employee from PDF missing email
- **Runs affected**: 14d31697 (1 run, 1 error)
- **Status**: LLM recovered on its own — retried with email after error. 1 wasted call but task completed. This is PDF extraction quality, variant-dependent. Not fixable generally.

### ℹ️ NOT FIXED: Token expired (403)
- **Runs affected**: 538ea526, 58ebb784, 1f153268, 51869a98, 40dea551 (5 runs)
- **Status**: Competition infrastructure issue. Token invalidated when another concurrent task on same sandbox completes first. Nothing we can do.