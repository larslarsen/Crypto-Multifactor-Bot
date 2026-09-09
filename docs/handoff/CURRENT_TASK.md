# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Eight of eleven products are accepted: membership, hourly bars, hourly trade flow, open
interest, realized funding, indicative funding, mark/index/basis and observed liquidation.
Review 476 accepts the real Batch A and Batch B products. Record 477 is Hermes's completed
integration, single-run and reconciliation evidence for Batch B.

## Current action

Batch B is complete and accepted. Integration:
`f83653c8747e627d9e8ceb2b88973e16556602f3`; Hermes publication:
`8a589baf0d298724fc753ff4d26c22a8dba7f8bc`; liquidation completion:
`dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f`.
The one run exited 0 in 297.4 seconds. All 37,890 files and 479,340 source-bound rows,
schemas, hashes, values, ordinals and typed gaps were independently reviewed; output uses
136,197,937 bytes within the unchanged 187,270,569-byte allocation.

The declared 18-entry secondary-source comparison is accepted as bounded reconciliation:
12 exact price/funding pairs, three measured BTC OI differences and three unavailable ETH OI
overlaps. OI differences are not equality passes and their cause remains unproven. The
liquidation product retains its observed/censored base-asset semantics and unknown availability.
Review 476 contains the acceptance limits and corrects Record 477's workflow chronology.
Do not rerun completed source checks, integration, conversion or accepted-product audits
without specific evidence of an invalidating defect.

Review 474's fixed completion checklist remains governing. The reviewer's next action is to
bound and authorize Batch C cost calibration under the existing ADR-0026 contract. Batch D
then covers the coverage/gap product and daily intersection, remaining Gate-4 reconciliation,
pinned bundle, catalog publication and clean NautilusTrader readback. Original quarantine,
holdout, replay and final acceptance requirements remain. No later-batch implementation or
next ticket is authorized yet. Gate 2 stays accepted; Gate 3 and CEX-002 remain IN_PROGRESS.

Governing documents:

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
