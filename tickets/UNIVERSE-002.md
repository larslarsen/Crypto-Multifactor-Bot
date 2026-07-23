# UNIVERSE-002 — Birdeye DEX New-Listing Event Feed

**Priority:** P1
**Status:** ACCEPTED
**Decision:** AUTHORIZED
**Dependencies:** ASOF-001 (accepted), REF-001 (accepted substrate), UNIVERSE-001 (accepted), EXP-001 (accepted)
**Layer:** universe / event source
**Architecture:** extends research substrate gate item #11 (historical universe snapshots) with a forward DEX listing-event stream; ADR required (new external source — see DF-08 authority boundary)

## Objective

Ingest **forward-only DEX new-token listing events** from the Birdeye Data Services API
as an additive low-cap/DEX universe source that the current CEX-bars universe
(UNIVERSE-001, Binance/Bybit) does not cover at all.

Each event records that a token became tradable on a DEX at a known time
(`liquidityAddedAt`), enabling a point-in-time "which DEX tokens existed as of T"
membership stream **from the ingestion start date forward**.

## Explicit Non-Goals / Hard Constraints

- **EVENT DATA ONLY.** This ticket ingests token *listing events* (appearance/creation).
  It does **NOT** fetch, backfill, or store OHLCV/price bars of any kind.
- **NEVER backfill bars against the Birdeye key.** The free Standard tier is a hard
  30,000 CU/month cap with no overage; OHLCV backfill would exhaust it in a handful of
  tokens. Bar acquisition remains the domain of BAR-001 (CEX) and is out of scope here.
- **NOT survivorship-free.** Birdeye provides listing/creation events but **no
  delisting / token-death feed**. This closes the *listing-side* gap forward only; it
  does **not** resolve DF-08 (`NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY`). Dead-token
  reconstruction on the CEX side is partially resolved at Aware-level via UNIVERSE-003
  (CMC survivorship backfill). This feed must be labeled non-survivorship-free
  everywhere it is surfaced.
- **Forward-only.** No historical membership reconstruction prior to ingestion start.

## Source Authority (must pass before ACCEPT)

Per the DF-x precedent, a new external source requires its own source-authority review.
Verified capability probes (2026-07-22, free Standard key, read-only):

- `GET /defi/v2/tokens/new_listing` → HTTP 200 on free tier. Returns
  `{address, symbol, name, decimals, source, liquidityAddedAt, liquidity, logoURI, ...}`.
- Auth is **per-API-key** (header `X-API-KEY`); no IP/geo dependency (429 only on the
  1 rps burst limit, not location). No VPN routing required.
- Free Standard tier: **30,000 CU/month, 1 rps**, API key required.
- Measured cost: `new_listing` ≈ 1–3 CU/call (credit counter is eventually-consistent;
  ~10 calls consumed ~30 CU total in probe).

Open authority gates for reviewer:
1. Licensing / terms-of-use for storing Birdeye listing events in the repo substrate.
2. Event completeness: is `new_listing` a complete listing feed or a sampled/trending
   subset? (Affects whether membership is authoritative or best-effort.)
3. `liquidityAddedAt` semantics: known-time vs effective-time; timezone; revisions.
4. Chain scope: which chains are covered on free tier (Solana confirmed; others TBD).

## Required Contract (on authorization)

- Poller reads `BIRDEYE_API_KEY` from environment (stored in gitignored `.env`;
  never committed).
- Calls `new_listing` only. IPv4-pinned (host egresses IPv6 to Cloudflare by default).
- Respects 1 rps; polls at a daily-TF-appropriate cadence (e.g. every 5–10 min) that
  stays well inside 30,000 CU/month.
- Dedupes by token `address`; appends new events to an event store keyed by
  `(chain, address, liquidityAddedAt)`.
- Deterministic, fail-closed on missing/malformed data or non-200 responses.
- `universe_events_since(decision_time)` — returns listing events at/after a time,
  as-of consistent (integrates with ASOF-001).
- Hard guard: the module must have **no code path that requests OHLCV/bar endpoints**.

## CU Budget (free tier)

- 30,000 CU/month, no overage. Poll `new_listing` only.
- ~2 CU/call × every 10 min ≈ 4,320 calls/month ≈ well under 30k with headroom.
- Every 5 min ≈ 8,640 calls/month ≈ ~17k CU — still fits. Choose cadence at build.
- Reserve remaining budget; do NOT add per-token detail lookups without re-budgeting.

## Data Source

- Birdeye Data Services — `GET /defi/v2/tokens/new_listing`.
- Chains: Solana confirmed on free tier; BSC/others pending gate #4.
- **No OHLCV. No historical backfill. Listing events only.**

## Deliverables

- `src/cryptofactors/universe/birdeye_listings.py` (event ingestion + as-of accessor)
- Public exports from `cryptofactors.universe`
- ADR: new external source + DF-08 authority boundary (forward listing events ≠
  survivorship-free universe)
- Ticket + governance records
- Tests + gates (Jr)

## Out of Scope

- OHLCV / price bars of any kind (hard constraint above)
- Historical membership reconstruction before ingestion start
- Delisting / token-death detection (not available from Birdeye)
- Factor computation, portfolio simulation
- Any use of the Birdeye key for non-listing endpoints

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/universe/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/universe tests/universe`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/universe tests/universe`
4. `python3 scripts/check_repo_control.py`
5. Test asserting **no OHLCV/bar endpoint is ever constructed** by this module
   (guard against accidental backfill).

## Phased Ownership

- Sr Dev (Grok): production source only. Stop for reviewer.
- Jr Dev (Hermes): tests, gates, records, Git, commit, push after approval.

## Stop Condition

Draft only. Return control to Reviewer for source-authority decision
(`Next ticket authorized: NONE`). No production source, tests, or ingestion until
authorized. DF-08 `NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY` remains in force; this feed
does not override it.
