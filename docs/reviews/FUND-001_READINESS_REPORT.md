# FUND-001 — Binance Funding-Cashflow Readiness Report

**Ticket:** FUND-001
**Status:** AWAITING_REVIEW
**Next ticket authorized:** `NONE`
**Next required actor:** Jr Dev - Hermes
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
- `last_funding_rate`: observed numeric field/value. Its provider unit, sign, and formula are not
  documented in accepted evidence; repository evidence does not establish cashflow semantics.

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
The accepted inventory records the sampled funding archive at
`retrieved_utc=2026-07-18T13:00:05Z`. That proves local raw-object acquisition time only; it does
not prove historical provider publication or 2025 strategy availability.

- `funding_time` / `calc_time`: provider event time only.
- `availability_time`: earliest defensible availability boundary; unknown in the archive evidence.
- `system_acquisition_time` / `source_publication_time`: not established by accepted evidence.

Unknown availability semantics remain fail-closed.

## 5. Corrections, Replacement, Quarantine

Accepted Binance archive evidence from other archive families shows replacement-aware archive
lineage and provider-side checksum validation. Funding-specific `.CHECKSUM` availability, match, and
replacement applicability remain unverified. Missing rows do not prove zero funding.

## 6. Proposed Non-Governing Event Contract

Non-governing proposal only.

- `dataset_type`: `funding_rate_event`
- logical key: `(venue_id, instrument_id, funding_time)`
- logical event key is stable across source reissues.
- raw object ID and provider checksum identify acquired bytes.
- manifest dataset ID identifies one normalized version.
- supersession links corrected datasets.
- dataset/raw IDs are lineage, not part of the logical event key.
- `source_dataset_id` is lineage and stays separate from logical identity.
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

- `FUND-002 - Binance Funding Source Semantics Audit`
- bounded official archive samples: BTCUSDT January 2025, BTCUSDT February 2025, ETHUSDT January
  2025
- ZIP, `.CHECKSUM`, response-header, official-documentation, and licensing evidence
- raw-outside-Git paths plus an evidence register with URLs, retrieval UTC, status, hashes, sizes,
  coverage, and documentation citations
- deterministic gates for `calc_time`, interval scope/change behavior, rate unit/sign/formula,
  provider publication/historical availability, funding-specific checksum/replacement behavior,
  licensing, and raw lineage
- fail-closed rule: any unknown mandatory semantic produces `NO_IMPLEMENTATION_AUTHORITY`

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
