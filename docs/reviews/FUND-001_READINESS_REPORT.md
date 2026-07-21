# FUND-001 — Binance Funding-Cashflow Readiness Report

**Ticket:** FUND-001
**Status:** AWAITING_REVIEW
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Recommendation
**SOURCE_EVIDENCE_REQUIRED**

Accepted repository evidence is enough to keep the readiness gate open, but not enough to publish a
canonical funding product. The current schema is non-governing. The source layer can define a
`funding_rate_event`, not a realized cashflow.

## 1. Source Semantics

See `research/fund_001/source_semantics_matrix.csv`.

- `calc_time`: observed 13-digit UTC epoch milliseconds in Binance monthly funding rows. It is only
  an observed provider event timestamp; repository evidence does not prove settlement time,
  publication time, or mark-price time.
- `funding_interval_hours`: observed value `8` in the captured BTCUSDT January 2025 sample. It is an
  observed interval field only; other values/instruments/months are unknown.
- `last_funding_rate`: observed numeric funding-rate decimal. It is the source rate field only;
  repository evidence does not establish cashflow semantics, sign semantics, or formula inputs.

## 2. Event vs Cashflow

Source normalization may eventually publish a `funding_rate_event` product. Realized funding cashflow
is downstream and requires position/notional, contract formula, settlement asset, price basis, and
sign semantics. Those fields do not belong in the event-row contract.

## 3. Identifier Reconciliation with REF-001

Accepted REF contracts use string identifiers. The accepted data architecture also requires compact
integer fact surrogates in Parquet. The unresolved issue is a deterministic string-to-fact-surrogate
mapping/public contract, not invalidation of either representation.

## 4. Time Semantics

The current schema already includes `availability_time`, `quality_flags`, and `source_dataset_id`.
Repository evidence does not establish `source_publication_time` or raw-object lineage in the schema.

- `funding_time` / `calc_time`: provider event time only.
- `availability_time`: earliest defensible availability boundary; unknown in the archive evidence.
- `system_acquisition_time` / `source_publication_time`: not established by accepted evidence.

Unknown availability semantics remain fail-closed.

## 5. Corrections, Replacement, Quarantine

Accepted Binance archive evidence and provider CHECKSUM sidecars show that archive objects can be
replaced and validated. Backfill must validate checksums and keep replacement history. Missing rows do
not prove zero funding.

## 6. Proposed Non-Governing Event Contract

Non-governing proposal only.

- `dataset_type`: `funding_rate_event`
- logical key: `(venue_id, instrument_id, funding_time)`
- lineage key: `source_dataset_id` kept separate
- canonical fields: `instrument_id` (REF string ID), `venue_id`, `funding_time`,
  `availability_time`, `funding_rate`, `interval_seconds`, `source_dataset_id`, `quality_flags`
- deterministic sort: `(venue_id, instrument_id, funding_time, source_dataset_id)`
- quality states: `PASS`, `PASS_WITH_WARNINGS`, `QUARANTINED`
- failure policy: quarantine if availability semantics are unknown or required fields are missing

This is non-governing and does not include downstream cashflow fields.

## 7. Native Inputs and Layer Boundaries

Preserve native settlement currency and native cashflow inputs. Do not invent USD conversion in
FUND-001. Later USD-denominated cashflow views remain blocked until FX source authority exists.

## 8. Follow-up Source Audit

Smallest next source audit, not executed here:

- official Binance monthly funding archive evidence for BTCUSDT January 2025 and BTCUSDT February
  2025
- official Binance archive/documentation evidence for timestamp semantics, interval semantics, rate
  unit/sign/formula, publication/availability, provider checksums/replacements, and licensing
- explicit pass/fail gates for archive availability, checksum verification, and documentation of any
  publication semantics

If this passes and the event/cashflow boundary still needs a public contract, a later ADR may be
required.

## 9. Records and State Transition

- `tickets/FUND-001.md`: set to `AWAITING_REVIEW`, record recommendation `SOURCE_EVIDENCE_REQUIRED`.
- `docs/handoff/CURRENT_TASK.md`: state `AWAITING_REVIEW`, next actor `Reviewer`, next ticket `NONE`.
- `docs/reviews/FUND-001_READINESS_REPORT.md`: this document.
- `research/fund_001/source_semantics_matrix.csv`: source-semantics matrix.
- `research/fund_001/platform_contract_matrix.csv`: platform-contract matrix.
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`: FUND-001 `AWAITING_REVIEW`.
- `README.md`: FUND-001 listed as `AWAITING_REVIEW`.

## Acceptance Command Evidence

`python3 scripts/check_repo_control.py`
Repo control check: PASS

## 10. Stop Condition

Commit and push the readiness records. Return control to Reviewer. Retain `Next ticket authorized:
NONE`. Do not begin implementation, schema migration, ADR, or source requests.
