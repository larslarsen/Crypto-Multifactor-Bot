# REF-002 - JR SOURCE AUDIT TASK

**Ticket:** `tickets/REF-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - SOURCE AUDIT AND RECORDS
**Next ticket:** `NONE`

## Assignment

Audit Bybit point-in-time instrument-event evidence. Do not edit executable files, tests, schemas,
migrations, ADRs, or generated datasets.

## Exact Candidate Procedure

1. Capture official linear `instruments-info` for BTCUSDT and its official 2020-03-25 trade archive.
2. Capture official inverse `instruments-info` for BTCUSDU26. Compare `deliveryTime` with retrieval
   time and classify it as scheduled/future or completed from evidence only.
3. Capture an official inverse `instruments-info` query with `status=Settled`. From returned records,
   select the lexicographically first symbol that has a positive `deliveryTime` earlier than retrieval
   time. Record the complete candidate set and deterministic selection.
4. For the selected settled instrument, capture its symbol-specific metadata, one official archive
   object immediately before/at its last observed trading date, and an official announcement search/
   retrieval attempt. If no qualifying settled record is returned, stop that branch and fail it
   explicitly.

## Evidence Requirements

Store raw bodies/headers outside Git under `/tmp/ref_002_raw`. Commit only hashes, complete metadata,
licensing-safe excerpts, and analysis.

Register every body and header request separately with:

- stable evidence ID/kind and exact URL/request parameters;
- retrieval UTC and HTTP/provider status;
- SHA-256, byte size, and exact external path;
- pagination cursor/request and complete candidate-selection evidence;
- provider event fields and UTC conversions;
- archive row count, first/last trade timestamps, and durable-gap limitation;
- announcement publication timestamp or exact failed attempt;
- documentation/revision/licensing citation.

No blank metadata is allowed for captured responses, including errors and empty bodies.

## Mandatory Gates

1. Instrument identity maps unambiguously to accepted REF venue/instrument semantics.
2. `launchTime`, `deliveryTime`, and `state` meanings are documented and correctly separated from
   retrieval/known time.
3. Historical archive edges corroborate economic validity without being mislabeled exact events.
4. Historical state transition and revision behavior are reconstructable, or explicitly fail.
5. Announcement publication time is captured for the settled event, or explicitly fails.
6. Prospective polling can preserve snapshots, cursors, known time, and corrections deterministically.
7. Raw lineage and licensing permit the intended internal evidence retention.

`HISTORICAL_EVENT_AUTHORITY` requires every gate to pass for both a listing and completed
delivery/delisting exemplar. `PROSPECTIVE_ONLY_AUTHORITY` requires gates 1, 2, 6, and 7 to pass while
historical gates fail. Otherwise recommend `NO_AUTHORITY`.

## Required Artifacts

- `docs/reviews/REF-002_SOURCE_FEASIBILITY_REPORT.md`
- `research/ref_002/EVIDENCE_REGISTER.csv`
- `research/ref_002/decision_matrix.csv`
- `research/ref_002/sources/bybit.md`

The decision matrix must be valid rectangular CSV and contain the single recommendation.

## Mechanical Validation

Validate register column counts, required non-empty fields, 64-character lowercase SHA-256 values,
nonnegative byte sizes, and existence of every external path. Record the literal PASS line and row
count in the report.

## Acceptance Command

Run `python3 scripts/check_repo_control.py` after all status changes and record the literal PASS
result. No pytest run is required because executable files may not change.

## Records And Stop Condition

- Add REF-002 to README/backlog and reconcile FUND-002 as accepted.
- Set REF-002 to `AWAITING_REVIEW`, name Reviewer as next actor, and retain
  `Next ticket authorized: NONE`.
- Commit, push, and stop. Do not begin implementation or another ticket.
