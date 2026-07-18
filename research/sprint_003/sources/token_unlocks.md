# Source note — Token Unlocks (Tokenomist / Messari / on-chain)

**Role:** REFERENCE_METADATA (unlock & vesting schedules) — currently DEFERRED
**Audit date:** 2026-07-18

## Status this audit: BLOCKED / DEFERRED

- **Tokenomist public API (`api.tokenomist.com`) was UNREACHABLE** from this environment:
  `urllib` raised `SSL: TLSV1_UNRECOGNIZED_NAME` (TLS handshake failure). Four token slugs
  (arb, apt, op, strk) all failed. No terms, no schema, no data could be confirmed.
- **Messari (`data.messari.io`)** returned HTTP 404/429 without an API key — trial/key
  required; treated as `EXPLORATORY_PHASE2` conditional (SRC-011).
- **DefiLlama emissions adapters** (see `defillama.md`) are a partial bridge but
  vintage-preservation is unverified.
- **On-chain vesting contracts** were not queried (need keys); they are the only
  authoritative point-in-time source for unlocks.

## Why this blocks DIL-01
`DIL-01` (Sprint 002, `H-011`) requires point-in-time: circulating/float supply, FDV,
unlock schedules, announcement/revision timestamps, and actual on-chain unlock events.
Per this audit we **cannot confirm that any public unlock chart preserves historical
schedule vintages** — current projections may not reflect information sets knowable on
past dates. Treating them as point-in-time would inject look-ahead.

## Required before promotion (SRC-010 condition)
1. Confirm Tokenomist (or alternative) reachability from the data-acquisition host.
2. Review licensing (some unlock data is licensed/commercial).
3. Determine whether historical schedule vintages are preserved, or only current
   projections shown.
4. Cross-check against: on-chain vesting contracts, project documentation, governance /
   announcement records, archived docs, and DefiLlama emissions adapters.
5. Prefer on-chain vesting queries as the canonical point-in-time unlock source.

## Licensing
Unlock aggregators often have commercial terms; do not commit or redistribute raw unlock
data without confirming applicable licenses.

## Gaps (explicit)
- Tokenomist unreachable (TLS). 
- Historical-schedule vintage preservation unconfirmed for every candidate source.
- On-chain vesting not yet queried.
