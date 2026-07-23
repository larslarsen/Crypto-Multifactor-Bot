# UNIVERSE-003 — CoinMarketCap Survivorship Backfill (CEX Dead-Coin Universe)

**Priority:** P1
**Status:** READY
**Decision:** AUTHORIZED
**Dependencies:** ASOF-001 (accepted), REF-001 (accepted substrate), UNIVERSE-001 (accepted),
DF-08 (`NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY` — this ticket seeks to partially close the
CEX side)
**Layer:** universe / source authority
**Architecture:** candidate authoritative historical membership source; ADR required
(new external source + DF-08 authority boundary)

## Objective

Evaluate and, if authorized, ingest CoinMarketCap's **inactive (dead) coin universe** with
birth/death dates as a one-shot **survivorship backfill** for the CEX side. This seeds the
pre-ingestion graveyard that a forward-only feed (UNIVERSE-002) structurally cannot recover,
directly targeting the DF-08 gaps G06 (delisted coverage) and G08 (reconstruction test).

## Distinction from UNIVERSE-002

- UNIVERSE-002 (Birdeye): forward DEX listing events; death = liquidity/volume → 0 (a state,
  not an event); forward-only; does not recover pre-ingestion dead tokens.
- UNIVERSE-003 (CMC): historical CEX-tracked dead coins with birth/death dates; one-shot
  backfill of the past graveyard. Complements, does not overlap, UNIVERSE-002.

## Verified Evidence (live probes, 2026-07-22, read-only, no API key)

Source replicates the crypto2 R package's core capability by calling CoinMarketCap's internal
`data-api` web back-end directly (crypto2 base64-obscures these URLs in its source). No R,
no key, Python stdlib only. Prototype: `scripts/research/fetch_cmc_dead_universe.py`
(currently in /tmp; to be committed under research on authorization).

- `GET data-api/v1/cryptocurrency/map?listing_status=inactive` → **1,756 dead coins**
  returned. Fields: `id, name, symbol, slug, is_active=0`. HTTP 200, status SUCCESS.
- `GET data-api/v3/cryptocurrency/detail?id=<id>` → per-coin dates. Sample run (25 coins):
  **23/25 had a death-proxy date** (`latestUpdateTime`); birth via `dateAdded` near-universal
  (`dateLaunched` sparser).
- Example: Devcoin (id 7) — dateLaunched 2011-07-22, dateAdded 2013-04-28,
  latestUpdateTime 2017-11-23. Bytecoin, BBQCoin, Yacoin, Franko, etc. all resolve.

## Date Semantics (must be reviewed — this is the crux)

- `dateAdded` / `dateLaunched` → birth (first_historical_data proxy). Adequate for
  point-in-time membership start.
- `latestUpdateTime` → **death-date PROXY** = when CMC stopped updating the coin. It is
  **NOT** an authoritative exchange delisting/halt time and carries **no final tradable
  price and no failure cause**.
- Consequence for DF-08: this likely satisfies G08 (reconstruction of historical membership)
  and materially improves G06 (delisted coverage), but does **NOT** fully satisfy G06's
  final-tradable-price / failure-cause requirement. Reviewer decides whether membership +
  death-proxy dates constitute sufficient authority for the intended experiments, or whether
  final-price/failure-cause is required (would need a different/paid source).

## Open Source-Authority Gates (reviewer)

1. **Licensing / ToS:** `data-api` is CMC's undocumented website back-end, not their official
   paid API. Terms-of-use and internal-retention authority for storing this data in the repo
   substrate must be established. (crypto2 is GPL/CRAN-published and does exactly this, which
   is precedent but not clearance.)
2. **Endpoint stability:** undocumented endpoint; may change without notice. Acceptable for a
   one-shot backfill; NOT for a recurring live dependency.
3. **Date authority:** is `latestUpdateTime` acceptable as a death proxy for the research
   use-case, given no final price / failure cause? (See above.)
4. **Coverage bound:** universe = CMC-tracked coins only. Coins that lived and died without
   ever being on CMC remain invisible (smaller residual graveyard — must be documented, not
   silently ignored).
5. **CEX vs DEX scope:** CMC tracks primarily CEX-listed assets; confirm this is the intended
   CEX-side complement to UNIVERSE-002's DEX side.

## Required Contract (on authorization)

- One-shot, read-only backfill script (no key, rate-limited, retry-then-skip).
- Two-step: inactive map → per-coin detail; dedupe by CMC `id`.
- Output: a survivorship-universe registry (CSV/parquet) with
  `{id, symbol, slug, name, birth_date, death_proxy_date, source, retrieved_at}`.
- Explicit provenance labeling: `death_date_is_proxy=true`, `source=cmc_data_api_unofficial`.
- Integrates with ASOF-001 for point-in-time membership queries.
- Deterministic; fail-closed on malformed/missing map response.
- Must NOT be wired as a recurring live dependency (endpoint stability gate #2).

## Deliverables

- `scripts/research/fetch_cmc_dead_universe.py` (the verified prototype, cleaned)
- `src/cryptofactors/universe/cmc_survivorship.py` (registry builder + as-of accessor)
- Public exports from `cryptofactors.universe`
- ADR: new external source, unofficial-endpoint risk, death-proxy semantics, DF-08 boundary
- The generated survivorship registry (or a documented regeneration procedure)
- Ticket + governance records
- Tests + gates (Jr)

## Out of Scope

- OHLCV / price bars for dead coins (final tradable price is a separate, harder problem;
  the map/detail endpoints do not provide it)
- Failure-cause classification
- Recurring/live polling of the unofficial endpoint
- Factor computation, portfolio simulation
- Coins never tracked by CMC

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/universe/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/universe tests/universe`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/universe tests/universe`
4. `python3 scripts/check_repo_control.py`
5. Test asserting provenance labels (`death_date_is_proxy`, unofficial source) are present on
   every registry row (no silent laundering of proxy dates into authoritative fields).

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

Draft only. Return control to Reviewer for source-authority decision
(`Next ticket authorized: NONE`). No production source, ingestion, or commit until authorized.
DF-08 `NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY` remains in force; this ticket proposes a
partial CEX-side closure subject to the gates above, and does not by itself override DF-08.
