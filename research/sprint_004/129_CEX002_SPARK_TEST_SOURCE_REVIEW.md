# CEX-002 Spark Test Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `e04bce90d019b68c0d2eb2e9a0b8909c1fb2d62f`

Governing review: `research/sprint_004/128_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md`

Reviewed hash:

| Path | SHA-256 |
|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `fbf90e899f34418952028455cb1cc87419f33951b7b42ed3b0a15c1e6c50dc1b` |

The test source contains 209 uniquely named test functions. Frozen production and CLI
hashes remain `6ef5c10c4ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d`
and `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96`.
The monolith remains exactly 1,059,297,547 bytes at SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.
The reviewer ran no pytest, Ruff, repository-control, network, data, candidate, migration,
or acceptance command.

## Decision

**ACCEPT AND FREEZE THE STORAGE-SUMMARY CORRECTION. REJECT ONE RESIDUAL RECEIPT ASSERTION
BEFORE HERMES INTEGRATION.**

The first corrected test now proves all four detailed collections are absent from the
storage surface and reconciles every storage summary counter, rule, family total, and
detail identity with the sole top-level manifest authority. That exactly closes review
128 finding 1 and must not change.

The second correction correctly abandons global raw-key absence and adds a structured
13-field-mapping check. Its final plan-reference proof is ineffective, however:
`sample_plan_keys` comes from `report.sample_plan["entries"]`, and the receipt necessarily
serializes that same sample plan. Proving that any such key appears in the receipt is
tautological. It does not establish review 128's required fact that at least one selected
manifest key is also a legitimate sample-plan reference. The helper also differs from the
specified exact complete-row comparison, making the assertion broader than the evidence
claim.

## Residual Spark authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized to edit only
the new compact-receipt assertion block inside
`test_compact_receipt_never_duplicates_the_detailed_manifest` in:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Replace `row_keys`, `_contains_full_manifest_row`, its assertion, and the current
`sample_plan_keys` assertions with the literal behavior below:

1. Serialize the already parsed `document` once with `sort_keys=True`,
   `separators=(",", ":")`, and `default=str`.
2. For every item in `rows`, serialize `dict(row)` with those exact arguments and assert
   that complete compact row object is not a substring of the compact receipt.
3. Build the selected-key set from `rows` and the sample-plan-key set from
   `document["sample_plan"]["entries"]`.
4. Require their intersection to be nonempty and require every key in that intersection
   to occur in the compact receipt.

Use the parsed `document`, not `report.sample_plan`, for the serialized plan proof. Preserve
the existing detailed-collection/surface-key assertions, the accepted storage-summary
correction, publication nonmutation assertions, and all other tests byte-for-byte. Do not
add or remove a test function or helper outside this local block. The unique test-function
count remains 209.

Every production, CLI, atomic, fixture, report, data, checkpoint, cache, progress, journal,
control, ticket, ADR, and unrelated path remains frozen. Spark performs no test, Ruff,
repository-control, network/data run, candidate execution, integration, record edit, Git
operation, commit, push, plan migration, sample acquisition, Gate 2, catalog, Nautilus,
Harmonic Trader, payoff, PAPER, LIVE, or other-ticket work. It stops for reviewer source
inspection with the exact test hash and 209 unique test-function count. Hermes remains
unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/129_CEX002_SPARK_TEST_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No test source, oversized report, ignored data, checkpoint, cache, journal, database
sidecar, or unrelated dirty path belongs to this publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Candidate execution and every next
ticket remain unauthorized. Next ticket remains `NONE`.
