# UNIVERSE-006 — Publish CMC Survivorship Graveyard as Catalog Universe Dataset

**Priority:** P0  
**Status:** AWAITING_REVIEW  
**Dependencies:** UNIVERSE-003 (ACCEPTED), ADR-0012, ADR-0014  
**Layer:** universe / catalog  
**Architecture:** one-shot CMC CSV → immutable catalog universe dataset (graveyard-only).
**No LIVE. No unofficial CMC polling loop. No composite tradable membership**
(composite deferred to follow-up ticket).

## Objective

Publish the existing `data/survivorship/cmc_dead_universe_full.csv` (1,756 dead coins) as a
**catalog-published** graveyard universe dataset so that `universe_at(t)` correctly excludes
dead coins at any point in time. Graveyard-only — tradable composite is a separate ticket.

## Scope

### In scope

1. Publish registry as catalog dataset type `universe_membership` (or existing universe type).
2. `CMCSurvivorshipProvider` loads from catalog/dataset path, not only loose CSV.
3. **All inactive coins without a death proxy date get `death_proxy_date = retrieved_at`**
   to prevent immortal membership (fail-closed).
4. Coverage window spans actual data range (min birth → max death/retrieved).
5. Catalog reconciliation calls `resolve_latest_by_type` and reports match result honestly.
6. Provenance fields preserved (`death_date_is_proxy`, `source=cmc_data_api_unofficial`).
7. Evidence report `research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json` with row counts,
   date coverage, sample as-of membership sizes, immortal-fix count.

### Out of scope

- Composite tradable membership (survivorship ∩ bar availability) — deferred to follow-up ticket.
- Fetching CMC again (re-use file; re-fetch only if regenerating one-shot with documented reason)
- Factor experiments
- DEX

## Acceptance (Jr)

1. Catalog contains universe dataset with ≥1,500 rows  
2. `universe_at(2020-01-01)` and `universe_at(2026-07-01)` return different sizes (sanity)  
3. pytest universe + control check PASS  

## Stop Condition

After Sr: AWAITING_REVIEW. Next: NONE (then DATA-011).
