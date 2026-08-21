# CEX-002 Focused Test Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `1436fba06ea2a5a2abffbcf2a2c6aa4d8885eaf3`

Subject record: `research/sprint_004/127_CEX002_REPORT_SPLIT_INTEGRATION_AND_CANDIDATE.md`

Integrated hashes:

| Path | SHA-256 | Disposition |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `6ef5c10c4ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d` | accepted and frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `7d046ce36d0912b728de7571cf49a227eda63191cb94fc9096f34b8fe5f67537` | rejected on two stale assertions |

Integration commit: `e0068e73192659ac3870aceeb03e2d2caa3402e7`.

Record-publication commit: `1436fba06ea2a5a2abffbcf2a2c6aa4d8885eaf3`.

The oversized report remains exactly 1,059,297,547 bytes at SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.
No corrected receipt or detail artifact was produced. The reviewer ran no pytest, Ruff,
repository-control, network, data, candidate, migration, or acceptance command.

## Decision

**ACCEPT THE INTEGRATION AND STOP DISCIPLINE. REJECT ONLY TWO REVIEWER-ACCEPTED STALE TEST
ASSERTIONS. PRODUCTION AND CLI REMAIN FROZEN.**

Hermes integrated exactly the three review-126 paths in `e0068e7`, pushed it, and left the
index and unrelated dirty work untouched. Focused command 1 collected 256 items and
reported 2 failed / 254 passed. Hermes then correctly ran none of commands 2-5, did not
preserve or replace the monolith, and did not start a candidate. Record 127 and its control
transition were published separately in `1436fba`. No workflow correction is required.

Review 126's source acceptance missed two accumulated test assertions. That is a reviewer
acceptance defect, not a reason to reverse the integration or alter ADR-0019.

## Findings

### 1. The old storage-row assertion contradicts ADR-0019

`test_manifest_rows_bind_identity_cadence_and_interval` still asserts
`report.storage["acquisition_manifest"]["rows"] == published`. ADR-0019 decision 4 makes
top-level `report.acquisition_manifest` the sole in-memory detailed owner and requires the
storage block to carry only a summary/reference. The production `KeyError: 'rows'` is the
intended architecture.

The test must retain its complete row-content, cadence, interval, integrity, and top-level
publication assertions. Replace only the stale storage-row equality with proof that the
storage manifest excludes `rows`, `collisions`, `rejections`, and
`raw_validation_pending_keys`, while its object/byte/consumable/pending counters, rules,
family totals, and detail summary agree with the top-level manifest authority.

### 2. Global key matching confuses plan evidence with row duplication

`test_compact_receipt_never_duplicates_the_detailed_manifest` already proves the four
detailed collection names and every selected/pending key are absent from both compact
acquisition-manifest surfaces. Its later global scan finds three selected kline keys in the
receipt and assumes they are duplicated detailed rows. Those keys are legitimate
`sample_plan.entries[*].key` values: the bounded execution plan is required low-cardinality
evidence and may reference a physical object also present in the selected manifest.

Keep the existing surface assertions. Replace only the invalid global `len(named) <= 1`
contract with a structural full-row proof: serialize the parsed receipt and each complete
13-field manifest row using the same compact, sorted-key JSON convention, and assert that
no complete row object occurs anywhere in the receipt. Also assert that this fixture has a
selected key in `sample_plan.entries` and that the legitimate plan reference remains in
the receipt, proving a key reference alone is not treated as row duplication. Do not
remove, redact, or summarize required plan, lineage, membership, storage, or source
evidence to satisfy the test.

## Spark test-only authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized to edit only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Spark makes exactly the two assertion corrections above. It must not delete either test,
weaken the complete manifest-row absence proof to field-name or raw-key absence, restore
rows to the storage surface, change production behavior, add a new abstraction outside the
test, or alter any other accumulated test contract. The unique test-function count remains
209.

The production module, CLI, atomic dependency and test, all fixtures, report 62, ignored
data, checkpoint, caches, progress, journals, controls, tickets, ADRs, and unrelated dirty
paths are frozen. Spark performs no test, Ruff, repository-control, network/data run,
candidate execution, integration, record edit, Git operation, commit, push, plan migration,
sample acquisition, Gate 2, catalog, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or
other-ticket work. It stops for reviewer source inspection with the exact test-path SHA-256
and the 209 unique test-function count. Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/128_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test path, oversized report, ignored data, checkpoint, cache, journal, database
sidecar, or unrelated dirty path belongs to this publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Candidate execution and every next
ticket remain unauthorized. Next ticket remains `NONE`.
