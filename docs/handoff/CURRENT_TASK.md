# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev - Codex Sol on GPT-5.6-sol High
Next ticket: NONE
Next ticket authorized: NONE

Seven of eleven products are accepted: membership, hourly bars, hourly trade flow, open
interest, realized funding, indicative funding and mark/index/basis. Review 476 accepts the
two real Batch A products after independent inspection of all 96,590 output files and bounded
source-backed economic checks. It corrects Record 475's premature acceptance/count claims
and artifact inventory without rerunning or changing accepted data.

Review 474's fixed completion checklist remains governing. The remaining order is B: observed
liquidation with secondary-source reconciliation; C: cost calibration; D: coverage/daily
intersection, remaining reconciliation, pinned bundle, catalog publication and clean
NautilusTrader readback. Original quarantine, holdout, replay and final acceptance requirements
remain. Gate 2 stays accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`.

## Current action

The owner explicitly authorizes direct prompting on 2026-09-08. The reviewer launches and
supervises Sol High for Review 476's Batch B source assignment. Only these new paths are
authorized:

- `src/cryptofactors/ingest/binance_usdm_liquidation_observed.py`;
- `scripts/research/normalize_binance_usdm_liquidation_observed.py`; and
- `tests/ingest/test_binance_usdm_liquidation_observed.py`.

All 569 liquidation responses and their inventory are already local. The drop preserves the
existing 15-column observed/censored schema, exact base-asset amounts and imbalance, full native
mapping/lineage, missing/unmapped gaps and immutable publication. It also produces the bounded
comparison evidence from the three retained Coinalyze overlap responses and accepted official
bar/OI/funding products. Review 476 fixes dates, fields, unit conversion and explicit missing
ETH OI overlap. No source substitution or new acquisition is needed for this source assignment.

Review 476 accepts the consolidated production corrections and freezes production at SHA-256
`2e001f2d63c6f127d58e7db0c071a2971ecb6a769d5bd1d85b322d085a1ee257` and CLI at
`8d97b52138c1ff27a39ddcc5b3fbb99f7db774ba5d0c948103d9d9b95830cfee`.
The one targeted run had 45 passes and one inconsistent off-grid fixture. Sol correctly stopped.
Sol High now corrects only that test fixture so its query identity matches the intentionally
off-grid bound, retaining both the grid and separate identity refusal assertions. It then runs
Review 476's exact targeted pytest command once under the senior-test exception, reports complete
output/hashes and stops; on nonzero, no patch or rerun. All other tests/paths, runtime checks,
real-data execution, network, integration, records and Git remain unauthorized. Hermes awaits
full source acceptance. Later batches and the next ticket remain unauthorized.

Governing documents:

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
