# FUND-002 - JR SOURCE SEMANTICS AUDIT TASK

**Ticket:** `tickets/FUND-002.md`
**Actor:** Jr Dev - Hermes
**Status:** INCOMPLETE - REVIEW-0094 EVIDENCE REGISTRATION REQUIRED
**Next ticket:** `NONE`

## Assignment

Audit Binance USD-M funding source semantics for the three exact monthly samples in FUND-002. Do not
edit production code, tests, schemas, migrations, ADRs, or generated datasets.

## Required Captures

Capture outside Git under `/tmp/fund_002_raw`:

- BTCUSDT January 2025 funding ZIP and `.CHECKSUM`;
- BTCUSDT February 2025 funding ZIP and `.CHECKSUM`;
- ETHUSDT January 2025 funding ZIP and `.CHECKSUM`;
- response headers for every request;
- exact official Binance documentation supporting timestamp, interval, rate unit/sign/formula,
  publication/update behavior, replacement/correction behavior, and licensing conclusions.

Commit only hashes, metadata, licensing-safe bounded excerpts, and analytical records.

## Evidence Register

For every request record a stable evidence ID, exact URL/request, retrieval UTC, HTTP status,
SHA-256, byte size, external path, response `Last-Modified`/equivalent or explicit absence, row count,
minimum/maximum `calc_time`, observed interval values, and documentation/terms citation.

Verify each provider `.CHECKSUM` against the downloaded ZIP. Do not infer funding-specific replacement
behavior from aggregate-trade evidence alone.

## Semantic Gates

Each gate passes only with exact official evidence and matching observed rows:

1. `calc_time`: provider definition establishes what event it timestamps and whether it represents
   scheduled funding, realized settlement, calculation, or another boundary.
2. Interval: unit and effective instrument/time scope are documented; all observed values and any
   changes are recorded without projecting current settings backward.
3. Rate: unit, positive/negative payer convention, formula meaning, and relationship to
   `calc_time` are documented.
4. Availability: provider publication time or a conservative historical availability bound is
   defensible. Local retrieval in 2026 alone cannot make a row available to a 2025 decision.
5. Corrections: funding ZIP checksum behavior and replacement policy/applicability are demonstrated.
6. Licensing: exact terms permit internal acquisition and committed metadata/hashes.
7. Lineage: raw bytes, provider checksum, raw object identity, normalized dataset version, and
   supersession responsibilities are unambiguous.

Any partial, assumed, current-only, contradictory, or unknown gate fails.

## Required Artifacts

- `docs/reviews/FUND-002_SOURCE_SEMANTICS_REPORT.md`
- `research/fund_002/EVIDENCE_REGISTER.csv`
- `research/fund_002/decision_matrix.csv`
- `research/fund_002/sources/binance.md`

Recommend exactly `EVENT_IMPLEMENTATION_AUTHORITY` only if every mandatory gate passes. Otherwise
recommend exactly `NO_IMPLEMENTATION_AUTHORITY` and list the first decisive blockers.

## Acceptance Command

Run exactly after final record changes:

`python3 scripts/check_repo_control.py`

Record the literal result. No pytest run is required because executable files may not change.

## Records And Stop Condition

- Reconcile FUND-001 as accepted under REVIEW-0093.
- Set FUND-002 to `AWAITING_REVIEW` in ticket, README, backlog, report, and handoff.
- Name Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, push, and stop.
- Do not begin implementation, realized-cashflow work, an ADR, or another ticket.
