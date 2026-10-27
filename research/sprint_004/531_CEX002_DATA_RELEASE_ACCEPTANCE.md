# CEX-002 Review531 — accept the complete CEX research data delivery

Reviewer: Lead Quantitative Finance Researcher/Engineer. Date: 2026-10-27 UTC.
Ticket: CEX-002. Decision: ACCEPTED under the explicit validation amendment below.
Next ticket: NONE. No strategy, scored study or new implementation is authorized.

## Decision and exact acceptance scope

Accept all eleven products in publication
`5ea22270b71064c94c4f6dc60f3f045219742a3130cfdb1293b6cbe47a99a30d`,
the Review529 dated-contract companion
`6ef47558eff2b3d3b30fbd8569dd96e0f7b7863bd8b310025cf641f7e72034a9`,
and the accepted HT-004/HT-005 data-consumer delivery. The complete counts, immutable
identities, coverage, economic checks and gate-by-gate evidence are in
[Review530](530_CEX002_FINAL_DATA_RELEASE_REVIEW.md). Its withheld ticket disposition
is superseded by this explicit reviewer decision; its recorded facts remain unchanged.

This is acceptance of the complete declared research data release. All eleven products,
the historical universe, typed gaps, exact source values and Nautilus delivery remain
required and delivered. No reduced symbol panel, price-only substitute or sampled release
is substituted for the full release. The bounded examples supplement previously accepted
full normalization/reconciliation and full consumer proofs.

## Explicit amendment to final validation

The original acceptance-evidence item1 required a successful repository-wide
`.venv/bin/python -m pytest tests/ -q --tb=short`. It has **not passed**. The owner stopped
that run and expressly opposed unrelated DEX work. Reviewer now replaces that global
software-health condition for **this data-release acceptance only** with the completed
CEX product-specific integration checks, full fixed-release data/consumer proofs, and
focused contract-history/consumer validation catalogued in Reviews525–530.

The other deliverable and evidence requirements remain in force. This changes the
acceptance criterion; it does not retroactively declare the original command successful.
The old collection exit2, interrupted retry exit143 and seven failure markers remain
recorded. The portion after interruption remains untested by that run. No assertion,
test source, skip marker, production source or expected result has been changed here.

Engineering basis: the delivered release has its own accepted source-bound normalization,
economic comparisons, coverage reconciliation, immutable file/catalog proof and full
Nautilus roundtrip. The consumer repair separately passed focused tests and real callbacks.
Those directly establish the data contract. A clean global software-health claim cannot
be made from these results, but it is not required to accept these exact delivered bytes
and consumer behavior. Closing this ticket does not certify reusable acquisition code
against every future input, the unrelated DEX subsystem, or the whole repository.

The following attribution supports keeping DEX repairs outside this ticket. Acceptance
does not depend on treating that reconstruction as a recovered runtime traceback.

## What the seven failure markers correspond to

The original Hermes session `20261026_174058_da9db4` was inspected read-only. Its launch
record100280 confirms the same unrelated dirty DEX engine/source tests were present.
Terminal record100329 confirms pytest143 and wrapper0. No preserved message supplies
failure names or tracebacks; its partial log is already embedded in Review530's attachment.

Read-only AST reconstruction used alphabetic acquisition-file order, source-definition
order and actual decorator parameter counts. It did not import test modules or execute
pytest collection. Relevant pytest ordering code and project configuration were inspected.
All test classes in this prefix have no inheritance; no custom collection hook or
parameterized fixture was found in the inspected acquisition tests. The installed plugin
entry points are AnyIO and Hypothesis. The source pins and method are retained below.

| Position in progress log (one-based) | Reconstructed test |
|---:|---|
| 1888 | `test_uniswap_v2.py::TestPairCreatedPilotEquivalence::test_existing_receipts_replay_identically_twice` |
| 2074 | `test_uniswap_v2_pair_events_v2_engine.py::test_production_attempt_atomic_success_and_lineage` |
| 2076 | `test_uniswap_v2_pair_events_v2_engine.py::test_production_journal_recovery_carries_authority_and_is_idempotent` |
| 2077 | `test_uniswap_v2_pair_events_v2_engine.py::test_production_startup_failure_replay_through_engine` |
| 2103 | `test_uniswap_v2_pair_events_v2_engine.py::test_production_startup_field_divergence_retains_journal[uniswap_v2_pair_event_v2_stage_attempt-domain_id-dom_x]` |
| 2126 | `test_uniswap_v2_pair_events_v2_engine.py::test_production_cleanup_before_either_unlink` |
| 2212 | `test_uniswap_v2_pair_events_v2_matrix.py::test_streamed_response_wall_expiry` |

All paths above are under `tests/acquisition/`. Each reconstructed name exactly matches
a retained failure-cache entry. An independent anchor also matches: the log's sole skip
at position1491 maps to `test_the_real_accepted_authority_completes_the_receipt_path`,
whose source explicitly skips when its local qualification authority is absent.

This is **strongly corroborated reconstruction**, not recovery of seven runtime reports.
The cache mixes old runs; it was not used to establish execution order. Source mtimes
predate the stopped run, and its launch dirty-path inventory matches, but the uncommitted
engine file was not hash-pinned at launch. No root cause or present pass/fail state is
claimed. No DEX tests, broad collection, live data queries or code repairs were run.

`python3 /tmp/cex002_triage531/reconstruct.py` exited0. Its source, AST count inputs,
file spans/hashes, exact parameter values, skip anchor, cache matches and two relevant
runner records are preserved in [the evidence attachment](cex002_failure_attribution_531.json).
SHA256: `6c37dbd7e2903ab46ae9e4ec023778be48ff5aa7bbfe23f7baf37a125ba2cc53`.
Initial cache-expanded ordering was rejected because obsolete parameter entries displaced
the skip anchor; only source-derived counts were used for the final reconstruction.
Initial optional config/temp-path probes found absent files or inaccessible unrelated
temporary directories; neither was read as evidence. No hidden failure was inferred away.

## Retained limits and stop condition

The 771-name universe includes 770 names with dated coverage across782 episodes; GAIB
is explicitly postponed/pending with no bars. All200 closed/snapshot-missing names are
included. Historical fee schedules, all dated order constraints and receipt times remain
incomplete. OI quote value is provider-reported. Liquidations are observed/censored.
Playback uses explicit timing/reference assumptions. None of these gaps is converted
to zero, complete history, tradability, actual funding entitlement or realistic fills.

The full dataset is available through the existing Harmonic Trader reader and documented
Nautilus command. No duplicate catalog or market-data copy is needed. The CEX data-delivery
task is finished; no further download, history crawl, data proof, test restart or model
work is assigned. The seven DEX findings remain recorded, unresolved and outside this
accepted data-release scope. No next ticket is authorized.

## Exact publication scope

CMB: this review, `research/sprint_004/cex002_failure_attribution_531.json`,
`tickets/CEX-002.md`, `docs/handoff/CURRENT_TASK.md`, and `README.md`.
HT-005 closeout synchronization: `docs/handoff/CURRENT_TASK.md`, `tickets/HT-005.md`,
and `README.md` only. Reviewer owns publication under the existing repair override.

Run repository-control and exact-path whitespace checks only; assert each staged path
set, commit/push and verify matching HEAD/origin with empty indexes. Preserve unrelated
work in both repositories. No production/test/data file is part of this publication.

Publication checks: CMB repository-control and scoped whitespace exited0; HT scoped
whitespace exited0 (HT has no repository-control script). Review links, evidence SHA
and the seven finding entries were checked successfully. No tests were executed.
