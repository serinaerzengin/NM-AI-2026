# Tripletex Agent — Issue Tracker & Changelog

Single source of truth for all known issues, fixes, and version history.
Auto-generated datasets: `runs_dataset.jsonl` (run logs), `task_dataset.jsonl` (task type specs).

---

## Current Score: ~78 pts (Leader: ~98 pts, Gap: ~20 pts)

## Open Issues (by score impact)

| ID | Gap | Task# | Task Type | Root Cause | Status |
|----|-----|-------|-----------|------------|--------|
| I-01 | 4.00 | 11 | `employee_onboarding_pdf` | Occupation code loop + PDF possibly not read by Gemini | v8: turn limits + v9: PDF input_file |
| I-02 | 3.00 | 12 | `project_lifecycle` | Delete/recreate timesheet loops, never invoices | v8: rule 15 workflow guidance |
| I-03 | 1.80 | 20 | `payroll` | arbeidsforhold error → auto-employment slow, LLM claims done | v7: auto-retry in apply_fixes |
| I-04 | 1.33 | 09 | `travel_expense` | paymentType missing, parallel costs → RevisionException | v7: skills update, v8: rule 12 |
| I-05 | 1.33 | 10 | `foreign_currency` | Minor agio/disagio calc errors | OPEN — needs investigation |
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
