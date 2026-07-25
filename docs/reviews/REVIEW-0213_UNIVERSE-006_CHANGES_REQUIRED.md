# REVIEW-0213 — UNIVERSE-006 CHANGES_REQUIRED

**Reviewer:** Strong Model (Lead Quant)
**Commit reviewed:** `6af29c5`
**Ticket:** UNIVERSE-006 — Publish CMC Survivorship as Catalog Universe

## What landed (keep)

- 1,756 rows published to exp003.db (PASS, REGISTERED)
- Provenance labels on every row (`death_date_is_proxy`, `cmc_data_api_unofficial`)
- No live CMC HTTP (CSV only)
- `live_eligible: false`
- Tests load real CSV + as-of smoke
- Publish script pattern matches other publishers

## Blocking issues (required before ACCEPTED)

### 1. `universe_at` immortal-membership bug
153 rows with empty `death_proxy_date` (all `is_active=False`) are *never* excluded — logic only checks death for `not is_active AND death_str`. Result: `universe_at(2026-07-01) == 153` = exactly the no-death set. Inactive without death ⇒ **fail closed** (exclude or set death=`retrieved_at` with label).

### 2. Ticket scope incomplete
Title + in-scope require a **composite** `alive ∩ quality bars ∩ screen` tradable universe. This is dead-only graveyard (zero active coins). Either implement composite or re-scope to "graveyard publish only."

### 3. Fake catalog reconciliation
`resolve_latest_by_type: null` with `match: true` is dishonest. Call the resolve or set `match` from real comparison.

### 4. Wrong coverage window
`event_start = event_end = now` on a 2011–2026 registry. Must span min birth → max death/retrieved.

## Verdict

**CHANGES_REQUIRED** — return to Jr Dev for fixes. 4 items above. No experiment reruns until composite exists.
