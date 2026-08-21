# CEX-002 Residual Focused Failure Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed source integration:
`8f08078a7a3aaf79f87b239b55fb20b3ee9a0a6e`

Reviewed execution publication:
`f9df83d646a32c38b3b031489b7f8376dcf0181d`

Integrated hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3453c1cfec2d3ee39d02eddf956e9a52438e101518bf5c6677a1f4d15a76071c` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4041f327f579eee773aa19d9345f325683916322cb5800b6461ec8b66e250ef2` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` |

## Decision

**ACCEPT THE EXACT INTEGRATION AND STOP DISCIPLINE. REJECT THE FOCUSED EXECUTION.
AUTHORIZE ONE BOUNDED CLAUDE CORRECTION.**

Hermes integrated and pushed exactly the two review-106 paths. Focused command 1 collected
189 cases and returned exit 1 with 186 passed and 3 failed. Hermes then correctly ran no
later focused command and did not invoke the real candidate process. No real candidate
report, version-3 proposal, or Gate-1 evidence exists to review.

## Production finding - proof changes outcome-blind cadence selection

`object_integrity_state` currently returns `checksum_proved_retained` whenever a key is in
`proved_keys`, even when that object's provider sidecar was absent from the pinned archive
listing. `select_nonoverlapping_objects` treats that state as selectable. A sample proof can
therefore make a previously rejected monthly package displace its daily fallback in the
final report. That violates the manifest contract: a listed provider sidecar is the
outcome-blind selection precondition, while re-proof may promote validation state only
inside that already eligible selection domain.

The integrity precedence must be:

1. quarantine remains quarantined;
2. absence from `checksum_keys` remains `sidecar_absent`, regardless of `proved_keys`;
3. a key present in both `checksum_keys` and `proved_keys` is checksum-proved; and
4. a key present only in `checksum_keys` is sidecar-listed and validation-pending.

Proof must not change monthly/daily cadence selection, create overlapping economic
coverage, or cause an unlisted-sidecar object to enter the acquisition manifest. It may
promote only an outcome-blind eligible row from pending to proved/consumable. The final
report-facing proof rebuild, checkpoint re-proof, provider-sidecar verification, immutable
locked plan, and sample execution order otherwise remain unchanged.

`test_manifest_uses_daily_fallback_for_an_unchecksummed_month` is a valid production
contract and must remain semantically unchanged. The focused unit contract must also prove
that `proved_keys={key}` cannot override `checksum_keys=set()`.

## Test finding - independent holdout boundaries are semantic

The two remaining identity failures compare independently created store roots without
pinning a common `now`. Each root correctly creates its own prospective holdout boundary at
its first authenticated qualification instant. `boundary_utc`, `boundary_ms`,
`boundary_id`, and `pinned_at` therefore differ. That is a real semantic difference, not
resume volatility, and it must not be removed from `identity_bytes` or added to
`_IDENTITY_DROP_KEYS`.

The tests must use one explicit timezone-aware fixed instant for the first qualification of
every independently created store being compared:

- `test_report_identity_matches_an_uninterrupted_run`; and
- `test_abort_after_completed_sample_resumes_missing_objects_only`.

Every invocation participating in each equality comparison must either receive that same
fixed `now` or replay the boundary pinned from that fixed first invocation. The assertions
must continue comparing complete `identity_bytes`; no prospective-holdout field may be
dropped, normalized away, or weakened. Existing separate holdout durability and replay
tests remain unchanged.

## Claude authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude implements only the integrity-precedence correction and the two fixed-boundary test
corrections above. The production correction should be localized to source-authority state
classification; it must not reselect or rewrite the locked plan. The CLI, all 17 fixtures,
the final proof rebuild, taker-flow logic, identity drop-key set, holdout implementation,
budget/ledger behavior, and every other test contract are frozen.

Claude performs no tests, Ruff, repo-control command, network/data run, migration,
integration, repository-record edit, Git operation, acquisition, catalog work, Nautilus
work, Harmonic Trader work, or publication. It stops for reviewer inspection and returns
the exact SHA-256 of both changed paths and the unique test-function count. Hermes and the
real candidate execution remain unauthorized.

## Reviewer publication

This review is a narrow reviewer-authored governance publication. The reviewer may stage,
commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/108_CEX002_RESIDUAL_FOCUSED_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, report, database sidecar, or unrelated dirty path belongs
to that commit. The reviewer ran no pytest, Ruff, repo-control, acceptance, network, data,
or migration command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Real candidate execution, Plan-3
mutation, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain
unauthorized. Next ticket remains `NONE`.
