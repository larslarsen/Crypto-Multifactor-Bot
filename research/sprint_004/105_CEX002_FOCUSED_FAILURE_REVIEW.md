# CEX-002 Focused Candidate Failure Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed source integration:
`f257a35cc6e57b84cc764d5674a2f2af186bddc8`

Reviewed execution publication:
`25c8e7408baee0e7a1be98218f49b7c58ae75515`

Integrated source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee142aabf0a3df589940ab982ff0087f9deacc593517fe856af9760a900c5bcd` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `6b3949e6e428e85e14febaf6a6725c487975da3e8421e206ed904442f08f7f1e` |

The 17 tracked fixture files were not part of the integration. Static counting still finds
170 uniquely named test functions.

## Decision

**ACCEPT THE EXACT SOURCE INTEGRATION. REJECT THE FOCUSED EXECUTION. AUTHORIZE ONE
BOUNDED CLAUDE CORRECTION.**

Hermes correctly preserved and integrated the three review-103 paths, committed and pushed
only those paths, and stopped before the real candidate-only process. The focused CEX-002
suite collected 189 cases and returned exit 1 with 177 passed and 12 failed. Therefore no
real candidate report, version-3 proposal, or Gate-1 evidence exists to review, and the real
command remains unauthorized.

Review 103 and both control files required a command failure to stop forward execution.
Hermes nevertheless ran commands 2 through 5 after command 1 failed. Those later commands
were read-only and the record shows no data consequence, but their results are void as
acceptance evidence. The corrected drop must restart the authorized sequence at command 1.

## Production finding 1 - final proof state is one execution late

`run_source_qualification` builds `acquisition_manifest` and `selected_storage` from only
the retained objects re-proved before plan execution. A normal run then downloads and
proves its planned objects, updates the checkpoint, and serializes the original pre-run
manifest and storage objects. The first report therefore describes newly completed objects
as pending/non-consumable; a resume rebuilds them as proved/consumable. This causes the five
resume/interruption identity failures. The acquisition manifest is semantic evidence and
must not be removed from `identity_bytes` or added to `_IDENTITY_DROP_KEYS` to conceal the
defect.

The correction must preserve the locked plan and all pre-execution planning inputs. After
normal execution, before matrix/report construction, it must build the final report-facing
manifest from proof established in the current invocation: retained object and provider
sidecar bytes re-proved at startup, plus newly acquired objects whose content and provider
checksum were validated during this invocation. It must not promote a checkpoint
`status=complete` claim without byte proof. The report-facing selected-storage and physical
requirement fields must be derived from that same final manifest. Candidate mode remains
read-only and uses only re-proved retained evidence. No plan selection, plan digest, lock,
ledger, download set, or execution order may change.

The existing identity tests are correct contracts and must remain semantically intact:

- `test_identity_bytes_stable_across_resume`;
- `test_report_identity_matches_an_uninterrupted_run`;
- `test_intact_sidecar_resumes_without_any_network_fetch`;
- `test_response_time_churn_replays_one_plan_and_keeps_identity`; and
- `test_rejected_live_authority_does_not_poison_a_later_resume`.

## Production finding 2 - retained taker-flow proof remains sample-pending

Candidate mode correctly re-proves a retained native one-hour kline object, recovers its
schema fields, and reports `supported=true` with zero fetches. The derived taker-flow row
then copies `bar_row.source_qualification_state` and `bar_row.release_blocked`. Because a
candidate intentionally acquires no samples, that bar row can be
`sample_evidence_pending` solely due to invocation mode. The copied state contradicts the
retained-schema evidence.

When retained schema proof is present and contains every required taker-flow field, the
derived row must remove only that artificial current-invocation sample-pending condition.
It must derive qualified official or typed-gap state from the underlying one-hour kline
authority and coverage. Real integrity, inaccessible-source, unresolved-membership, and
blocking-coverage conditions must remain visible and blocking. Missing, incomplete, or
unproved retained schema must remain sample-pending or integrity-blocked as appropriate.
No trade, aggregate-trade, or network fetch may be introduced.

## Stale and invalid test contracts

Six failures do not justify changing accepted production semantics:

- `test_resume_refuses_tampered_content_addressed_bytes` inventories only
  `monthly/trades`, now a discovery-only family. It must exercise a selected checksummed
  native one-hour kline object and retain the same tamper/refusal assertion.
- `test_derived_products_do_not_block_source_gate` still expects taker flow to be
  unsupported. With a valid native one-hour kline schema it must expect official derived
  authority and continue proving that derived outputs do not block the source gate.
- `_distinct_object_payload` always emits headerless trade rows, including for selected
  kline keys. It must emit deterministic, distinct, schema-valid kline ZIP bytes for kline
  keys and retain deterministic trade bytes for discovery-only trade keys. This correction
  must restore the interrupted-resume and transfer-accounting tests without weakening
  their assertions.
- `test_family_launch_gap_keeps_official_authority` tries to prove bar authority with
  `trades` and `aggTrades`, neither of which is a bar acquisition input. It must use an
  actual selected native one-hour kline family with a head family-launch gap and retain all
  official-authority, typed-gap, nonblocking, and temporal assertions.
- `test_no_public_switch_can_reselect_the_locked_plan` already checks the exact public
  parameter and exact prohibited CLI flag. Its whole-file `"relock" not in source`
  assertion rejects explanatory text and must be removed; the exact behavioral/static
  boundary assertions remain.
- Tests using `_trades_index(..., payload_for_key=_distinct_object_payload)` must continue
  to prove that absent distinct selected raw bytes cause a real transfer and that completed
  objects resume without refetch. The fixture repair, not a relaxed production path, owns
  those failures.

## Claude authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude implements only the two production corrections and six test-contract corrections
above. The CLI path and all 17 fixture files are frozen. Existing stable-identity, tamper,
provider-sidecar, no-refetch, transfer-accounting, exact-authority preflight, immutable
version-2 lineage, budget, secret-redaction, and candidate-zero-fetch guarantees must not
be weakened or deleted. No identity field may be masked merely to make a comparison pass.

Claude performs no tests, Ruff, control command, network/data run, plan or ledger
migration, integration, repository-record edit, Git operation, acquisition, catalog work,
Nautilus work, Harmonic Trader work, or publication. It stops for reviewer inspection and
returns the exact SHA-256 of both changed paths and the unique test-function count.
Hermes and the real candidate execution remain unauthorized.

## Reviewer publication

This review is a narrow reviewer-authored governance publication. The reviewer may stage,
commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/105_CEX002_FOCUSED_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, report, database sidecar, or unrelated dirty path belongs
to that commit. The reviewer ran no pytest, Ruff, repo-control, acceptance, network, data,
or migration command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Plan-3 mutation, real candidate
execution, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain
unauthorized. Next ticket remains `NONE`.
