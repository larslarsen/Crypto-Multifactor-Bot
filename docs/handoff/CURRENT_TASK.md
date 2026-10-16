# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev - Codex Sol
Next ticket: NONE
Next ticket authorized: NONE

Nine of eleven products are accepted. Review 480 accepts Batch C cost calibration,
finalizer integration `ab671b4713add0d9367c08cb18603f99b037fe1a`, Hermes publication
`d6d86e0900c051f938cdf91fb9ffeb6336baf766` and Record 479. Gate 2 remains accepted;
Gate 3 and CEX-002 remain IN_PROGRESS.

## Current action

Review 483 accepts Record 482 as the terminal failure disclosure and preserves source
acceptance. The integration and first real run succeeded; reconciliation failed twice,
including an unauthorized helper edit/retry. No passing reconciliation or replay exists.
Coverage data acceptance remains withheld. The schema mismatches are helper defects;
static review also finds missing predicate, summary, identity and metadata checks.

Review 483 rejects Longcat's first replacement helper on static inspection. The subsequent
Laguna preparation stopped without producing a replacement: a broad discovery command
failed, then the authorized exact-path continuation reached an internal approval timeout
and explicit denial for a completion-JSON inspection command. The command did not execute.
Both Hermes sessions are terminated. No new audit or producer replay occurred.

The owner-authorized read-only inspection succeeded. The reviewer stopped Hermes and
routed the complete reconciliation implementation to one Sr Dev - Codex Sol assignment
(GPT-6.1-sol High): a standalone repository research script and focused test source, under
Review 483's exact two-path scope and one targeted-test exception. This implements the
existing independent reconciliation requirements; no producer or architecture changes.

The senior stops for reviewer source inspection. Hermes retains integration, execution
and evidence ownership but is not yet authorized. No real audit, replay, source outside
the two paths, bundle, catalog, quarantine, accepted-product rerun, model or next ticket
is authorized. Existing helpers and data remain preserved.

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
