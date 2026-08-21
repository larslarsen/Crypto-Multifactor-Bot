# CEX-002 Ruff Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `fa96c1a45b9a2641f2a251962d9ae6d43dc17bd0`

Subject record: `research/sprint_004/131_CEX002_TEST_INTEGRATION_AND_CANDIDATE.md`

Integrated hashes:

| Path | SHA-256 | Disposition |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `6ef5c10c4ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d` | accepted behavior; F402 correction required |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `23f1159f8d664f0c55b26498ef69ea72196bb70279055ccf6f9da06dea0d550b` | 256 pytest items passed; F841 correction required |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` | accepted and frozen |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` | accepted and frozen |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` | 18 pytest items passed; frozen |

Test integration commit: `d428aecf20e92528f16905efce9fb75ae9ea4e68`.

Record-publication commit: `fa96c1a45b9a2641f2a251962d9ae6d43dc17bd0`.

The monolith remains exactly 1,059,297,547 bytes at SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.
It has not been copied to the prior-report content address. No candidate or data mutation
occurred. The reviewer ran no pytest, Ruff, repository-control, network, data, candidate,
migration, or acceptance command.

## Decision

**ACCEPT THE TEST INTEGRATION, C1/C2 RESULTS, AND STOP DISCIPLINE. ROUTE TWO LITERAL RUFF
CORRECTIONS TO SPARK.**

Hermes integrated only the review-130 test path, pushed it, and left the index and
unrelated dirty paths untouched. C1 passed 256/256 items and C2 passed 18/18. C3 then
reported exactly two errors and Hermes correctly stopped before C4, C5, monolith
preservation, snapshots, or candidate execution.

The record-131 publication updated `tickets/CEX-002.md` to the reviewer but left
`docs/handoff/CURRENT_TASK.md` naming Hermes. That mismatch is a publication defect. This
reviewer-authored publication repairs both controls to the same Spark actor; no developer
source, test, data, or evidence change is needed for the repair.

## Findings and exact corrections

### F402 production local name

At production lines 6488-6490, `for name, path, fields in history_specs` shadows the
imported `dataclasses.fields` helper added by ADR-0019. Rename only that local tuple target
from `fields` to `point_fields`, and change only the corresponding
`required_point_fields=fields` argument to `required_point_fields=point_fields`. This is a
lexical rename with no source, parsing, financial, network, or authority behavior change.

### F841 obsolete test bytes

At test line 6020, delete only `rendered = receipt_path.read_bytes()`. Spark's accepted
canonical receipt assertion no longer uses those raw bytes. Do not replace it and do not
change any assertion.

## Spark mechanical authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized to edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Spark makes exactly the two changes stated above. It must not format, reorder, refactor, or
touch any other line. The CEX test source retains 209 uniquely named test functions. Every
CLI, atomic, fixture, report, data, checkpoint, cache, progress, journal, control, ticket,
ADR, and unrelated path remains frozen.

Spark performs no test, Ruff, repository-control, network/data run, candidate execution,
integration, record edit, Git operation, commit, push, plan migration, sample acquisition,
Gate 2, catalog, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or other-ticket work. It
stops for reviewer inspection with exact SHA-256 values for both edited paths and the 209
unique test-function count. Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/132_CEX002_RUFF_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No production/test path, monolith, ignored data, checkpoint, cache, journal, database
sidecar, or unrelated dirty path belongs to this publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Candidate execution and every next
ticket remain unauthorized. Next ticket remains `NONE`.
