# Sr Dev prompt — UNIVERSE-006 (escalated from Jr after 2 failures)

Model: Grok Build (Sr). Owner relays once. Stop for reviewer at AWAITING_REVIEW.

## Goal

Fix `CMCSurvivorshipProvider` immortal membership bug, re-publish graveyard dataset with honest evidence, and commit. One pass.

## The bug

`src/cryptofactors/universe/cmc_survivorship.py` — inactive coins with no `death_proxy_date` are **always eligible** in `universe_at(t)` because the death check is:
```python
if not is_active and death_str:
    # only here we enforce death
```
Missing `else: always pass`. And `normalize_coin_record` does not fill missing death dates.

Jr's "fix" patched at publish-script time only — the provider itself is still broken. Anyone loading CSV gets immortal coins.

## Required source changes

### 1. Fix `universe_at` semantics (cmc_survivorship.py)

```python
# Rule: inactive AND no death_proxy_date → NOT eligible (unknown death ≠ alive)
if not is_active:
    if not death_str:
        continue  # unknown death → exclude
    death_dt = parse_iso_datetime(death_str)
    if death_dt and t > death_dt:
        continue
```

Do **not** fabricate `death=now`. Do **not** put fake dates in CSV data. The `universe_at` method itself must enforce the rule on whatever data it receives.

### 2. Fix publish script

- Load CSV → build provider → compute as-of counts from **provider** (already working).
- The script already publishes the provider's table. No separate row mutation needed if the provider is correct.
- Re-run and update `42_CMC_UNIVERSE_PUBLISHED.json`.

### 3. Add test

In `tests/universe/test_cmc_survivorship.py`:

```python
def test_inactive_without_death_is_excluded() -> None:
    provider = CMCSurvivorshipProvider.from_csv(csv_path)
    t = datetime(2030, 1, 1, tzinfo=timezone.utc)
    univ = provider.universe_at(t)
    # 153 rows have no death date — none should be eligible at any t
    for r in provider.records():
        if not r["is_active"] and not r.get("death_proxy_date"):
            assert r["instrument_id"] not in univ
```

## Evidence must show

After re-publish, `42_CMC_UNIVERSE_PUBLISHED.json` must contain:
- `resolve_latest_by_type: <dataset_id>` (not null)
- `match: true`
- `immortal_rows_fixed: 153` (the count of no-death rows that are now excluded)
- `universe_at_2026_07_01_count` ≠ old count (should be smaller)
- `coverage_window.event_start` = earliest birth date (~2013), not now
- `coverage_window.event_end` = latest death/retrieved date, not now

## Do not

- Touch DATA-010, DEX, or other dirt in the working tree
- Add features beyond the bug fix
- ACCEPTED — stop at AWAITING_REVIEW

## Scope re-scoped

Ticket UNIVERSE-006 is now "graveyard-only". No composite, no bar intersection. Composite deferred to DATA-011 or a follow-up.

## Stop

When all 5 items in CURRENT_TASK are done → commit → AWAITING_REVIEW. Tell owner.
