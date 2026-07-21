# FUND-001 - JR FINAL READINESS CORRECTION TASK

**Ticket:** `tickets/FUND-001.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Scope

Make only the six REVIEW-0092 corrections. Do not perform provider calls or edit code, tests,
schemas, migrations, ADRs, or generated datasets.

## Required Corrections

1. Set `last_funding_rate` observed unit to `UNKNOWN: provider unit/sign/formula not documented in
   accepted evidence`. Keep only numeric representation as observed.
2. Record local system acquisition time as the raw object's accepted `retrieved_utc`. Keep provider
   publication time and historical availability time unknown; explain that retrieval in 2026 cannot
   establish availability to a 2025 strategy decision.
3. State precisely that Binance replacement/checksum mechanisms are demonstrated for other archive
   families. Funding-specific `.CHECKSUM` availability, match, and replacement applicability remain
   unverified.
4. Rewrite `platform_contract_matrix.csv` as valid five-column CSV with every comma-bearing field
   quoted. Use `funding_rate_event` for the proposed event product; use `funding_cashflow` only when
   referring to the rejected draft or downstream realized-cashflow layer.
5. State exact lineage:
   - logical event key is stable across source reissues;
   - raw object ID and provider checksum identify acquired bytes;
   - manifest dataset ID identifies one normalized version;
   - supersession links corrected datasets;
   - dataset/raw IDs are lineage, not part of the logical event key.
6. Define but do not start exactly one proposed follow-up:
   `FUND-002 - Binance Funding Source Semantics Audit`.

The FUND-002 proposal must name:

- bounded official archive samples: BTCUSDT January 2025, BTCUSDT February 2025, ETHUSDT January
  2025;
- ZIP, `.CHECKSUM`, response-header, official-documentation, and licensing evidence;
- raw-outside-Git paths plus an evidence register with URLs, retrieval UTC, status, hashes, sizes,
  coverage, and documentation citations;
- deterministic gates for `calc_time`, interval scope/change behavior, rate unit/sign/formula,
  provider publication/historical availability, funding-specific checksum/replacement behavior,
  licensing, and raw lineage;
- fail-closed rule: any unknown mandatory semantic produces `NO_IMPLEMENTATION_AUTHORITY`.

Retain exactly one current recommendation: `SOURCE_EVIDENCE_REQUIRED`. FUND-002 is proposed only and
is not authorized by this task.

## Acceptance Command

Run exactly after final record changes:

`python3 scripts/check_repo_control.py`

Record the literal result. No pytest run is required.

## Records And Stop Condition

- Mark the prior correction task `INCOMPLETE - REVIEW-0092` and this task `COMPLETED` only after the
  report and both matrices agree.
- Set FUND-001 to `AWAITING_REVIEW`, name Reviewer as next actor, retain
  `Next ticket authorized: NONE`, commit, push, and stop.
- Do not create or start FUND-002, an ADR, or implementation.
