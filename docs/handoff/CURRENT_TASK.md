# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Jr Dev — Hermes
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

Review 474's fixed completion checklist remains governing. Review 478 accepts the corrected
Batch C source; Sol's sole targeted pytest run passed all 38 cases. Hermes integrated the
three paths at commit `e092d17afa3d229135d89fa144ddc2b120e8e2f7` and pushed; `HEAD == origin/main
== e092d17afa3d229135d89fa144ddc2b120e8e2f7`. Hermes ran exactly one foreground local
conversion with a 43,200-second allowance. The run failed at `_enforce_component_bounds`
with exit 1: `retained_book_ticker measured allocation exceeded`. Measured ticker rows
882,076,090 exceed the bound 745,543,507 by 136,532,583 rows. All other components are within
bounds. No completion descriptor was published. Record 479 preserves the failed run;
Review 478 corrects its row-total/timing details and pins the verified preserved output.
Review 478 accepts the finalizer source after Sol's fixture correction and 30 passing
focused cases. Hermes now owns its complete integration, preserved-output finalization,
one successful replay proof and in-place Record 479 update. Reuse all 7,731 existing
files and publish only the verified completion, preserving the exceeded projection and
every byte limit. Follow the current finalizer workflow in Review 478; earlier producer
assignments are history. No repeated conversion is authorized.

Batch D follows with coverage/daily intersection, remaining Gate-4 reconciliation, pinned
bundle/catalog and clean NautilusTrader readback. Original quarantine, holdout, replay and
final acceptance requirements remain. No Batch D or next ticket is authorized. Gate 2
stays accepted; Gate 3 and CEX-002 remain IN_PROGRESS.

Governing documents:

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
