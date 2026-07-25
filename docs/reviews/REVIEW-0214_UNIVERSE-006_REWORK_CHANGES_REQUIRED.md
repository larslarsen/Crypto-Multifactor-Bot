# REVIEW-0214 — UNIVERSE-006 Rework CHANGES_REQUIRED (Escalated to Sr)

**Reviewer:** Strong Model (Lead Quant)  
**Base commit:** `6af29c5` (uncommitted working-tree edits)  
**Actor:** Jr Dev (failed twice → escalated per policy)

## Jr fixes attempted (per REVIEW-0213)

1. **Immortal membership** — publish-time `death_proxy_date = now` on `table.to_pylist()`
2. **Scope** — ticket re-scoped to graveyard-only ✓
3. **Reconciliation** — `resolve_latest_by_type` added to script
4. **Coverage window** — min/max dates computed

## Why STILL CHANGES_REQUIRED

1. **Evidence never re-run** — `42_CMC_UNIVERSE_PUBLISHED.json` still old data
2. **Provider not fixed** — `cmc_survivorship.py` unchanged; `universe_at` on unfixed provider
3. **`death=now` doesn't fix history** — all 153 still alive for any `t < now`
4. **No test** for the fail-closed rule

## Verdict

**CHANGES_REQUIRED — escalated to Sr Dev (Grok Build).** Jr failed twice on same root cause.

See CURRENT_TASK.md for Sr brief.
