# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Jr Dev - Hermes
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

Review 474 accepts Sol's complete three-file Batch A source drop. Its one authorized targeted
pytest invocation passed all 50 cases (exit 0), and the reviewer reproved the frozen hashes.
Hermes now owns the complete integration, validation, one local run and evidence workflow for:

- `src/cryptofactors/ingest/binance_usdm_price_state.py`;
- `scripts/research/normalize_binance_usdm_price_state.py`; and
- `tests/ingest/test_binance_usdm_price_state.py`.

The drop consumes the already downloaded generation-0 mark/index/premium authority and produces
two separate products with the frozen schemas. Review 474 contains the exact accepted hashes,
ordered checks, integration steps, one foreground command, 7,200-second execution allowance,
source-count cross-checks and complete terminal-record requirements. Preserve the enumerated
relative authority paths and use `data/.cex002_price_state` as the new hidden output root.

The owner relays Review 474's complete workflow to Hermes. Successful steps need no intermediate
approval or review. Hermes stops on the first nonzero result or failed proof, preserves output,
and publishes Record 475 plus these control records, returning both actor fields to the reviewer.
No source patch, retry, acquisition, next batch or next ticket is authorized. Sol's assignment
is complete. Source acceptance does not accept unexecuted products; five remain accepted.

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
