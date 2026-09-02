# CEX-002 Review 443 — Record 442 Review and Evidence Correction

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject Record 442 as written; authorize one record-only evidence correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted publication and artifact facts

Hermes commit `a90f70cf4401e13d2014d26f6ab0116ebb5c57d3` changed exactly Record 442,
CURRENT_TASK, and CEX-002 and is pushed with `HEAD == origin/main`. Repository control and the
commit whitespace check pass. The completion descriptor content hashes to its content-addressed
name `bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4`.

The published evidence agrees on 19,744 Parquet partitions, 19,744 lineage documents, empty
staging, 160,226,578 physical rows, 75,255 byte-identical repeated rows, 2,818 excluded
adjacent-midnight spillovers, and 160,148,505 product rows. It also reports verified
descriptor-referenced hashes, 57,441 quality-gap rows, the one fixed HBARUSDC provider checksum
conflict, authenticated authority totals, and output bytes by artifact class. The reviewer found
no data, source, schema, capacity, or acquisition defect.

## Record defects

Record 442 is not accepted as written.

1. It labels the descriptor filesystem mtime `2026-09-01 17:48:46 -0700` as
   `2026-09-01 17:48:46Z`. The correct UTC conversion is
   `2026-09-02T00:48:46.152177890Z`. Against the recorded start
   `2026-09-01T21:26:20Z`, the elapsed wall time is approximately 3 hours 22 minutes 26 seconds,
   not approximately 65 minutes.
2. The Review-437 supervisor produced no durable terminal-status record. The corrected evidence
   must describe the UTC descriptor-publication mtime and absent identities precisely; it must not
   claim an observed process exit code or exact completion time that the runner did not record.
3. Review 437 required exact per-lineage spillover and identical-repeat reconciliation. Record 442
   states only descriptor totals and does not publish the lineage aggregate proof.
4. Review 437 required preservation proof for all 181 pre-existing partition/lineage pairs.
   Record 442 lists only twelve 0GUSDT row counts, describes them as calendar-length-consistent
   despite partial boundary months, and does not prove all 181 prior artifact bytes.
5. Record 442 and CURRENT_TASK claim both actor fields returned to the reviewer, but the ticket's
   top-level actor remained Jr Dev — Hermes. This review makes Hermes the explicit next actor for
   the correction and requires both fields to return together afterward.

These are evidence-record defects. They do not authorize mutation or replay of the completed data.

## Exact Hermes correction

Hermes performs one read-only evidence correction and publishes
`research/sprint_004/444_CEX002_OPEN_INTEREST_TERMINAL_EVIDENCE_CORRECTION.md`. It:

- records the exact local descriptor mtime with offset, its exact UTC conversion, the recorded
  start UTC, and the correct approximate elapsed wall time;
- distinguishes descriptor publication plus absent process identities from an unavailable
  supervisor exit status;
- scans the 19,744 descriptor-referenced lineage documents and publishes the exact aggregate
  counts for the accepted identical-repeat and spillover fields, proving they equal 75,255 and
  2,818 respectively, with any nonmatching result terminal;
- identifies all 181 partition/lineage pairs published before the Review-437 start, proves each
  path remains descriptor-referenced and each current content digest equals its content-addressed
  filename, and publishes the count and aggregate digest of a deterministic sorted inventory;
- corrects the twelve-month 0GUSDT statement to coverage-boundary language or omits it; and
- carries forward the already published descriptor, row, gap, authority, schema, and artifact-byte
  facts without expanding scope.

Hermes updates CURRENT_TASK and CEX-002, returns both actor fields to the reviewer, stages exactly
those three record paths, commits, pushes, proves `HEAD == origin/main`, and stops. No source,
test, CLI, data, descriptor, lineage, Parquet, runner, wrapper, acquisition, test execution,
cleanup, replay, next product, experiment, model, trading-engine work, or next ticket is
authorized.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/443_CEX002_RECORD442_REVIEW_AND_EVIDENCE_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All implementation, data, runner, wrapper, and unrelated dirty paths remain unstaged and
untouched.
