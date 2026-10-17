# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev — Grok Build (grok-4.7 High)
Next ticket: NONE
Next ticket authorized: NONE

## Current action

Review 489 authorizes Grok's five-path source/test implementation of the remaining
bounded one-minute/hourly kline reconciliation. Grok is active in native Build with
normal approvals. Use the nine exact daily sample dates and ten role bindings from
the pinned qualification report; implement bounded sample acquisition, offline exact
aggregation/comparison, CLI and tests. Only Review 489's single targeted test is
assigned after source is ready. Stop on its first failure and return source for review.
No real download or comparison run, integration, data/catalog mutation, bundle,
experiment or next ticket is authorized. Hermes has finished Record 488 publication.

The owner reports almost all Grok usage remains and access ends tomorrow night.
Prioritize Grok for substantive senior source work while preserving reviewer acceptance
and bounded integration ownership. Do not rotate merely for planning latency.

## Accepted state and remaining release work

Gate 0 is ACCEPTED in Reviews 485 and 487. Five invalid BitMEX datasets are
REJECTED/REGISTERED and excluded by the default resolver; real application and
idempotent replay passed with all ten historical artifacts unchanged. Source 49e307e
and Record 486 publication 4ff8bf4 remain accepted. The separate strict normalizer/
publisher correction is integrated at f85177d9f1d21fe1fd054d40035afbf62b4e457f;
Hermes passed 52 targeted cases, Ruff/control/whitespace, then published Record 488
at 68e93069acfdaa0a2fc9d7d606f75feaa4fcd49f. Review 487 independently reconciles the
six committed source hashes and accepts the completed gate. Grok's extra syntax check
and Hermes's malformed Git-object probe/post-failure inspection remain disclosed.
Do not rerun quarantine, source tests or accepted-product audits without a specific defect.

Ten of eleven Binance products are accepted; Gate 2 remains ACCEPTED. Gate 3 and
CEX-002 remain IN_PROGRESS. Review 474's fixed completion checklist still governs.
Coverage source 867c47a and Record 484 publication becb6d2 are accepted in Review 483:
replay reused completion 9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151,
after-audit PASS, all 107,590 files / 543,901,501 bytes unchanged. Observed five-product
days are 428,090; full-cadence days with event presence are 424,431. These remain distinct
from known source availability. No further coverage replay/audit is assigned.

Cost completion fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e is
accepted: 3,865 partitions, 939,130,319 book rows, 939,131,092 component rows and
17,943,795,556 bytes. The 136,532,583-row ticker projection excess and
ordinary_sizing_check_passed=false remain explicit; byte bounds pass. Prior exact
inventory/replay evidence is preserved.

Batch D still owes remaining Gate-4 comparisons, the pinned harmonic bundle/catalog,
clean NautilusTrader readback, release replay and original final acceptance commands.
Accepted fee scenarios, unknown availability and observed/censored liquidation semantics
remain unchanged. Holdout: 2026-08-21T16:19:08.994166+00:00. Reviewer acceptance is
exclusive; no full-ticket acceptance, modeling or next ticket is authorized.

Governing documents:

- research/sprint_004/489_CEX002_BOUNDED_KLINE_RECONCILIATION_SOURCE_REVIEW.md
- research/sprint_004/488_CEX002_BITMEX_NORMALIZER_INTEGRATION_RECORD.md
- research/sprint_004/487_CEX002_BITMEX_NORMALIZER_SOURCE_REVIEW.md
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
