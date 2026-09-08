# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev - Codex Sol on GPT-5.6-sol High
Next ticket: NONE
Next ticket authorized: NONE

Review 474 fixes the existing completion checklist in `tickets/CEX-002.md`. Five of eleven
products are accepted: membership, hourly bars, hourly trade flow, open interest and realized
funding. Gate 2 remains accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`.

The remaining order is A: indicative funding plus mark/index/basis; B: observed liquidation
with its secondary-source reconciliation; C: cost calibration; D: coverage/daily intersection,
remaining reconciliation, pinned bundle, catalog publication and clean NautilusTrader readback.
The original quarantine, holdout, replay and final acceptance requirements still apply.
This is the same ticket and release contract. Update current status in place; historical
review narratives remain in the ticket, research records and Git history.

## Current action

The owner explicitly authorized direct delegation on 2026-09-08. The reviewer launches and
supervises Sr Dev - Codex Sol using GPT-5.6-sol High for Review 474. Sol may author only:

- `src/cryptofactors/ingest/binance_usdm_price_state.py`;
- `scripts/research/normalize_binance_usdm_price_state.py`; and
- `tests/ingest/test_binance_usdm_price_state.py`.

The drop consumes the already downloaded generation-0 mark/index/premium authority and uses
its frozen schemas to produce two separate products. It preserves signed premium inputs,
explicitly unavailable indicative rates, causal joins, declared exact-decimal basis arithmetic,
full lineage and typed gaps. Publication remains partition-bounded, immutable and replayable.
Review 474 contains the complete authority, economic, publication and test-source contract.

Sol returns the three paths with SHA-256 and line counts for reviewer static inspection.
Sol performs no tests, real-data run, integration, records, Git, acquisition or data mutation.
Hermes integration and execution require reviewer source acceptance. No later batch, model,
experiment, Harmonic Trader work or next ticket is authorized.

Governing documents:

- research/sprint_004/474_CEX002_FIXED_CLOSEOUT_AND_PRICE_STATE_SOURCE_AUTHORIZATION.md
- research/sprint_004/473_CEX002_REALIZED_FUNDING_ACCEPTANCE.md
- research/sprint_004/460_CEX002_HOURLY_KLINE_PRODUCT_ACCEPTANCE.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- docs/adr/0024-typed-normalization-and-partition-atomic-publication.md
- docs/adr/0025-complete-product-sizing-and-fee-authority.md
- docs/adr/0026-non-backdated-fee-scenarios.md
- docs/engineering/DEVELOPMENT_ROLES.md
- tickets/CEX-002.md
