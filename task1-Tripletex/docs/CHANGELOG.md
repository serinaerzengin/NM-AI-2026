# Tripletex Agent — Issue Tracker & Changelog

Single source of truth for all known issues, fixes, and version history.
Auto-generated datasets: `runs_dataset.jsonl` (run logs), `task_dataset.jsonl` (task type specs).

---

## Current Score: ~78 pts (Leader: ~98 pts, Gap: ~20 pts)

## Open Issues (by score impact)

| ID | Gap | Task# | Task Type | Root Cause | Status |
|----|-----|-------|-----------|------------|--------|
| I-01 | 4.00 | 11 | `employee_onboarding_pdf` | pdfplumber missing from Dockerfile + occupationCode stripped + entitlement skipped | **v10: FIXED** (5 root causes addressed) |
| I-02 | 3.00 | 12 | `project_lifecycle` | Delete/recreate timesheet loops, never invoices | v8: rule 15 workflow guidance |
| I-03 | 1.80 | 20 | `payroll` | arbeidsforhold error → auto-employment slow, LLM claims done | v7: auto-retry in apply_fixes |
| I-04 | 1.33 | 09 | `travel_expense` | paymentType missing, parallel costs → RevisionException | v7: skills update, v8: rule 12 |
| I-05 | 1.33 | 10 | `foreign_currency` | LLM thinking loop timeout (197s without acting) | **v11: FX workflow in system prompt** |
| I-06 | 1.27 | 13 | `cost_analysis` | Pagination truncates ledger data | v7: fullResultSize fix |
| I-07 | 1.20 | 25 | `ledger_error_correction` | Slow individual posting lookups, sometimes times out | OPEN — needs batch strategy |
| I-08 | 1.09 | 29 | `project_hours_invoice` | Stale cache after POST, activity confusion | v9: cache invalidation |
| I-09 | 1.06 | 17 | `monthly_closing` | Single combined voucher | v8: rule 16 separate vouchers |
| I-10 | 0.60 | 30 | `?` | Unknown | OPEN |
| I-11 | 0.27 | 06 | `custom_dimension_voucher` | Wrong field names (dimension1 vs freeAccountingDimension1) | v9: apply_fixes auto-rename |

## Closed Issues

| ID | Issue | Fixed In | How |
|----|-------|----------|-----|
| C-01 | Proxy token expired → entire run dies | v6 | ProxyTokenExpiredError detection + abort |
| C-02 | Bank account not set → invoice fails | v6 | Proactive ensure_bank_account on startup |
| C-03 | File attachments crash (Unhandled item type) | v7 | Wrap in {"role":"user","content":[...]} + input_text/input_image types |
| C-04 | Project missing startDate | v6 | apply_fixes default |
| C-05 | Employee missing userType | v6 | apply_fixes default |
| C-06 | Travel expense cost missing amount field | v6 | apply_fixes amount→amountCurrencyIncVat |
| C-07 | apply_fixes crashes on list payloads | v7 | isinstance(payload, dict) guard |
| C-08 | Logs unreadable (scattered, no turn tracking) | v7/v8 | RunHooks + RunLogger |
| C-09 | LLM ignores time/turn pressure | v7.1 | Dynamic instructions with turn_count |
| C-10 | Occupation code brute-force loop | v7.1 | nameNO search guidance + turn limit |
| C-11 | Gemini API hangs indefinitely | v7.2 | 90s client timeout + 240s asyncio timeout |
| C-12 | GET cache stores truncated responses | v9 | Still truncated but cache invalidated on mutations |
| C-13 | POST/PUT don't invalidate cache | v9 | _invalidate_cache on POST/PUT/DELETE |
| C-14 | PDF sent as input_image (wrong MIME) | v9 | Changed to input_file type |
| C-15 | Posting truncation strips VAT/currency | v9 | Added vatType, currency, supplier, customer to _slim_values |
| C-16 | Dimension field auto-rename | v9 | apply_fixes renames dimension1→freeAccountingDimension1 |

---

## Version History

### v11 (00072, 2026-03-22)
**Focus: Fix 3 verified production issues from scoring analysis**

1. **FIXED: Auto-onboard employment conflict (Issue 1)** — `auto_onboard_employee()` was creating employment with `startDate=TODAY` which conflicted when the LLM later tried to create employment with the correct startDate from the PDF/prompt (409 RevisionException). Fix: removed auto-employment from onboard, only ALL_PRIVILEGES grant remains. LLM handles employment since it knows the correct startDate. Verified on sandbox: 0 errors, correct startDate.
2. **FIXED: Supplier invoice dueDate strip (Issue 4)** — LLM sent `dueDate` on POST /supplierInvoice → 422 "Feltet eksisterer ikke" → wasted 1 call + 1 error. Fix: `apply_fixes.py` now strips `dueDate` from supplierInvoice payloads automatically.
3. **FIXED: FX payment workflow visibility (Issue 2)** — FX workflow was only in `skills/put.md` which loads on first PUT call. But the LLM gets stuck thinking BEFORE making any PUT. Fix: moved FX step-by-step workflow into system prompt so LLM sees it from turn 0. Added "do NOT spend time analyzing postings — just register payment and book difference."
4. **FIXED: Dynamic instructions had wrong time budget** — Said "120s budget" but actual budget is 240s. Updated thresholds: warn at 120s, critical at 180s.

Files changed: `apply_fixes.py`, `agent.py`, `system_prompt.py`

### v10 (2026-03-22)
**Focus: Task 11 (employee_onboarding_pdf) — 0/4.0 → targeting full score**

Root cause analysis found 5 issues, all fixed:

1. **CRITICAL: pdfplumber missing from Dockerfile** — pyproject.toml had it but Dockerfile did not. All PDF extraction failed in production. Agent fabricated employee data instead of reading the contract. This single bug caused the entire 0 score.
2. **occupationCode stripped by apply_fixes** — `payload.pop("occupationCode", None)` removed it from every employment details POST. The GET endpoint actually works (proven by runs 08ed9fb1, 438753da). Removed the stripping.
3. **System prompt said occupationCode is [BETA]/403** — Wrong. Rewrote rules 16-17 with correct occupation code lookup strategy: `?nameNO=KEYWORD`, max 3 attempts, then skip.
4. **Entitlement (admin role) often skipped** — Was in separate rule 10, not in PDF workflow. Now step c in the mandatory 7-step workflow (a-g) with "MANDATORY" label.
5. **employmentType enum values undocumented** — Agent guessed wrong values from non-English PDFs (e.g. "FAST"). Added all valid enums: ORDINARY/MARITIME/FREELANCE, PERMANENT/TEMPORARY, MONTHLY_WAGE/HOURLY_WAGE/etc.

Also added:
- **File-saving logic in api.py** — Saves incoming files (PDFs, CSVs, images) to `received_tasks/{req_id}/` with prompt.txt and metadata.json. Enables local analysis of competition data and task replay.
- `received_tasks/` added to .gitignore

Files changed: `Dockerfile`, `apply_fixes.py`, `system_prompt.py`, `api.py`, `.gitignore`

### v9 (00054, 2026-03-22)
- Cache invalidation on POST/PUT/DELETE (not just DELETE)
- Dimension field auto-rename in apply_fixes
- PDF as input_file instead of input_image
- Less aggressive posting truncation (added vatType, currency, supplier, customer)
- Dimension guidance in system_prompt + skills/post.md

### v8 (00053, 2026-03-21)
- Consolidated logging (RunLogger → one stderr block per run)
- DELETE clears GET cache
- System prompt rules 15-17: project hours workflow, separate monthly closing vouchers, PDF employee limits
- Prompt log truncation increased to 800 chars

### v7.2 (00050, 2026-03-21)
- Gemini API timeout: 90s per call
- asyncio.wait_for: 240s hard timeout
- max_turns: 40→30

### v7.1 (00049, 2026-03-21)
- Turn-based pressure in dynamic instructions (warn at 12, critical at 20)
- Occupation code search guidance (nameNO, max 2 attempts)
- Anti-loop rule 14

### v7 (00048, 2026-03-21)
- File attachment fix (SDK-compatible input format)
- RunHooks logging (TURN/THINK/CALL/EXEC)
- Dynamic instructions (callable, time/error/call pressure)
- "GETs are free" scoring rule
- Admin entitlement guidance (rule 10)
- Pagination fullResultSize exposure
- Travel expense paymentType rule + skills update
- Project invoicing/activity skills
- apply_fixes list payload guard
- perDiemCompensation location default

### v6 (00047, 2026-03-21)
- Proxy token 403 detection + abort
- Bank account proactive setup
- Project startDate, employee userType defaults
- Travel expense field fixes
- System prompt endpoint index + rules
