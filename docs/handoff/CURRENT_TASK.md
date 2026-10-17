# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Nine of eleven products are accepted. Review 480 accepts Batch C cost calibration,
finalizer integration `ab671b4713add0d9367c08cb18603f99b037fe1a`, Hermes publication
`d6d86e0900c051f938cdf91fb9ffeb6336baf766` and Record 479. Gate 2 remains accepted;
Gate 3 and CEX-002 remain IN_PROGRESS.

## Current action

Coverage replay and independent reconciliation have succeeded; terminal publication and
reviewer acceptance remain to be completed. GPT-6.1 Sol High's checker/test source is
accepted and integrated at `867c47a4d26b4c4e49bae13450a0ce8103ef2f69`. The 71 final-byte tests
and first real audit remain preserved. No passing test or before-audit was rerun.

Fresh Hermes session `20261016_174722_4c2f0d` (Longcat 2.5 free) executed one standalone
replay: actual exit 0, completion_reused=true, unchanged completion
`9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151`.
The after-audit returned exit 0 PASS; separate inventory cmp exited 0. All 107,590 files
and 543,901,501 bytes retain identical path/hash/size/inode/mtime entries. The observed-day
count is 428,090; full-cadence days with event presence are 424,431. The correction of an
initial wrong completion filename and earlier denied attempts remain disclosed in Record
484 / Review 483; none is erased by successful execution.

Hermes's remaining assignment is evidence continuation and exact three-path publication
under Review 483. These current fields are reviewer-authored for that publication.
After it, stop for reviewer disposition. Nine products remain accepted pending that
review; Gate 2 ACCEPTED, Gate 3/CEX-002 IN_PROGRESS, next NONE. No further replay/audit,
source/helper changes, bundle, catalog, quarantine, other-product rerun, model or next ticket.

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

The holdout is pinned at 2026-08-21T16:19:08.994166+00:00. Gate 0 remains unfinished:
Review 480's read-only query of exp003.db finds all five invalid BitMEX datasets still
PASS / REGISTERED. A separate corrective assignment is required before final release;
quarantine and catalog mutation are outside the current coverage source scope.
No bundle publication, full-ticket acceptance, experiment, model or next ticket is
authorized now.

Governing documents:

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
