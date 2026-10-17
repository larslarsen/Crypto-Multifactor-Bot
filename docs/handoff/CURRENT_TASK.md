# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Ten of eleven products are accepted. Review 483 accepts coverage source integration
`867c47a4d26b4c4e49bae13450a0ce8103ef2f69`, the Record 484 continuation, and Hermes
publication `becb6d259663258fbc5eb2cd50911b462848b896`. Gate 2 remains accepted;
Gate 3 and CEX-002 remain IN_PROGRESS.

## Current action

Coverage is ACCEPTED. The standalone replay exited 0, reused completion
`9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151`, and the independent
after-audit exited 0 PASS. Separate inventory cmp exited 0: all 107,590 files and
543,901,501 bytes retain identical path/hash/size/inode/mtime entries. Observed five-product
days remain 428,090; full-cadence days with event presence remain 424,431. The 71 final-byte
tests and first audit were preserved, not rerun. No further coverage replay/audit is assigned.

Review 485 accepts Sol's seven-path quarantine/resolver source integration 49e307e.
Hermes passed 225 quarantine/catalog tests, Ruff/control/whitespace and the real dry-run
(exit 0). The corrected read-only inspection also passed on Step 3.7 Flash. Those results
were preserved and were not rerun. Longcat's helper TypeError, Step-5 upstream-capacity
failure and Step-3.7 inference stall remain disclosed.

Under Review 485's owner-approved bounded execution exception, Grok Build (grok-4.6 High)
ran the remaining application and replay once each, reconciled the three reports against
independent file hashes and SQLite mode=ro catalog rows, and published Record 486.
Application exited 0: disposition=applied, applied=true, all five REJECTED/REGISTERED and
ineligible. Replay exited 0: disposition=replayed, applied=false, idempotent_replay=true,
same quarantine metadata. Ten manifest/Parquet artifacts retain identical
path/hash/size/device/inode/mtime/ctime/mode entries. Economics remain 307,738 rows, zero
null/nonzero rates, 307,738 empty intervals, symbol counts [2,5,5,5,45]. Control returns
to the reviewer. Gate 0 remains open: the separate normalizer/publisher correction is
unassigned. Reviewer acceptance is exclusive. Ten Binance products remain accepted. No
bundle, experiment or next ticket is authorized.

Accepted cost completion:
`fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e`.
The reviewer independently reconciled 7,732 files, 3,865 partitions and matching lineages,
939,130,319 book rows, 939,131,092 total component rows and 17,943,795,556 output bytes.
All 7,731 preserved files retain identical hashes/inodes/mtimes. The 136,532,583-row ticker
projection excess remains explicit with `ordinary_sizing_check_passed: false`; all byte
bounds pass. Hermes's successful finalization and authorized byte-identical replay are
accepted. Do not rerun the producer, finalizer or accepted-product audits without a
specific invalidating defect.

Review 474's fixed closeout still governs Batch D: coverage/daily intersection, remaining
Gate-4 comparisons, pinned bundle/catalog, clean NautilusTrader readback, release replay
and original final acceptance commands. Observed-day overlap must remain distinguishable
from complete daily coverage and known source availability. Accepted Batch B comparison
limits, fee scenarios, unknown availability and censored liquidation semantics remain.

The holdout is pinned at 2026-08-21T16:19:08.994166+00:00. Gate 0 remains unfinished.
Record 486 reports the five BitMEX catalog rows as REJECTED/REGISTERED after authenticated
application and no-op replay; immutable manifests and Parquets were not rewritten. The
separate BitMEX missing-to-zero/unconditional-PASS normalizer/publisher correction remains
pending. Reviewer acceptance is exclusive.
No bundle publication, full-ticket acceptance, experiment, model or next ticket is
authorized now.

Governing documents:

- research/sprint_004/486_CEX002_GATE0_QUARANTINE_INTEGRATION_RECORD.md
- research/sprint_004/485_CEX002_GATE0_QUARANTINE_SOURCE_REVIEW.md
- research/sprint_004/483_CEX002_COVERAGE_RECONCILIATION_RECOVERY_REVIEW.md
- research/sprint_004/482_CEX002_COVERAGE_INTEGRATION_AND_REAL_RUN_RECORD.md
- research/sprint_004/484_CEX002_COVERAGE_RECONCILIATION_AND_REPLAY_RECORD.md
- research/sprint_004/481_CEX002_COVERAGE_CORRECTION_REVIEW.md
- research/sprint_004/480_CEX002_COST_ACCEPTANCE_AND_COVERAGE_SOURCE_AUTHORIZATION.md
- research/sprint_004/478_CEX002_COST_CALIBRATION_SOURCE_AUTHORIZATION.md
- research/sprint_004/479_CEX002_COST_CALIBRATION_INTEGRATION_AND_REAL_RUN_RECORD.md
- research/sprint_004/477_CEX002_LIQUIDATION_INTEGRATION_AND_REAL_RUN_RECORD.md
- research/sprint_004/476_CEX002_PRICE_STATE_ACCEPTANCE_AND_LIQUIDATION_SOURCE_AUTHORIZATION.md
- research/sprint_004/475_CEX002_PRICE_STATE_INTEGRATION_AND_REAL_RUN_RECORD.md
- research/sprint_004/474_CEX002_FIXED_CLOSEOUT_AND_PRICE_STATE_SOURCE_AUTHORIZATION.md
- research/sprint_004/445_CEX002_OPEN_INTEREST_PRODUCT_ACCEPTANCE.md
- research/sprint_004/460_CEX002_HOURLY_KLINE_PRODUCT_ACCEPTANCE.md
- research/sprint_004/473_CEX002_REALIZED_FUNDING_ACCEPTANCE.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- docs/adr/0024-typed-normalization-and-partition-atomic-publication.md
- docs/adr/0025-complete-product-sizing-and-fee-authority.md
- docs/adr/0026-non-backdated-fee-scenarios.md
- docs/adr/0027-partition-aware-dictionary-storage-sizing.md
- docs/engineering/DEVELOPMENT_ROLES.md
- tickets/CEX-002.md
