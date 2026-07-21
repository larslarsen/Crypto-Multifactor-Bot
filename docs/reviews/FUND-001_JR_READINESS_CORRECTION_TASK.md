# FUND-001 - JR READINESS CORRECTION TASK

**Ticket:** `tickets/FUND-001.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Scope

Correct the existing report and two matrices using repository evidence only. Do not perform network
requests or edit production code, tests, schemas, migrations, ADRs, or generated datasets.

## Required Corrections

1. Inventory the draft schema accurately: `availability_time`, `quality_flags`, and
   `source_dataset_id` already exist; source publication/acquisition time and raw-object lineage do
   not.
2. Limit observed Binance semantics to exact evidence:
   - `calc_time` is a 13-digit millisecond timestamp field in the sampled archive;
   - `funding_interval_hours` is `8` in the sampled BTCUSDT January 2025 rows;
   - `last_funding_rate` is the observed numeric source field.
   Do not assign settlement, publication, sign, formula, mark/index, or interval-ending meaning
   without evidence.
3. State that neither archive `calc_time` nor REST `fundingTime` proves a distinct publication time.
4. Reconcile IDs correctly: REF exposes stable string IDs; architecture requests compact integer
   surrogates in fact Parquet. Record the missing deterministic mapping/public contract instead of
   declaring either representation invalid.
5. Separate layers:
   - source normalization may eventually emit a `funding_rate_event` product;
   - realized funding cashflow remains downstream and requires position/notional, contract formula,
     settlement asset, price basis, and sign semantics.
   Remove downstream cashflow fields from any proposed event-row contract.
6. Use one event product name consistently. Keep stable logical event identity separate from raw and
   dataset lineage; do not include `source_dataset_id` in the logical event key.
7. Preserve unknown availability semantics as a fail-closed blocker. Do not claim as-of publication
   readiness while earliest defensible availability is unknown.
8. Retain exactly one recommendation: `SOURCE_EVIDENCE_REQUIRED`. Mention a possible later ADR only
   as a deferred consequence after source semantics pass, not as a competing current decision.
9. Define one exact smallest follow-up source audit, including candidate official Binance archive/
   documentation evidence, bounded symbols/months, timestamp and interval semantics, rate unit/sign/
   formula, publication/availability, provider checksums/replacements, licensing, raw lineage, and
   explicit pass/fail gates. Do not execute it in FUND-001.
10. Correct all artifact paths and make report and matrices agree.

## Acceptance Command

Run exactly after final record changes:

`python3 scripts/check_repo_control.py`

Record the literal result. No pytest run is required because executable files remain untouched.

## Records And Stop Condition

- Mark the original readiness task `INCOMPLETE - REVIEW-0091` and this task `COMPLETED` only after all
  corrections are published.
- Set FUND-001 to `AWAITING_REVIEW`, name Reviewer as next actor, and retain
  `Next ticket authorized: NONE`.
- Commit, push, and stop. Do not start the source audit, an ADR, implementation, or another ticket.
