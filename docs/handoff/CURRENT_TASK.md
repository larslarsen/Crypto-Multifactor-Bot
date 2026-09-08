# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Review 474 fixes the existing completion checklist in `tickets/CEX-002.md`. Six of eleven
products are accepted: membership, hourly bars, hourly trade flow, open interest, realized
funding, and the Batch A price-state pair (indicative funding plus mark/index/basis). Gate 2
remains accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`.

The remaining order is B: observed liquidation with its secondary-source reconciliation;
C: cost calibration; D: coverage/daily intersection, remaining reconciliation, pinned bundle,
catalog publication and clean NautilusTrader readback. The original quarantine, holdout, replay
and final acceptance requirements still apply. This is the same ticket and release contract.
Update current status in place; historical review narratives remain in the ticket, research
records and Git history.

## Current action

Record 475 publishes the Review-474 integration and real-run outcome. Hermes reproved
`HEAD == origin/main == a5699e7b60e3123be1514021d796b1d927c58698` and all three accepted
hashes/line counts. The three ordered integration commands passed (pytest 50/50, ruff clean,
check_repo_control.py PASS). Hermes integrated the three paths at commit
`a5699e7b60e3123be1514021d796b12927c58698` and pushed; `HEAD == origin/main == a5699e7b60e3123be1514021d796b1d927c58698`.
Preproof: output root absent, 229,433,143,296 available bytes (above 110,648,021,942 floor).
Hermes ran exactly one foreground command and remained attached until terminal.

The command exited 0 at 3,479 seconds (~58 minutes). Indicative completion SHA-256
`360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0`, 15,153,756 product
rows, 21,507 partitions, 1,115 gap artifacts, 0 unjoinable source rows. Basis completion
SHA-256 `b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0`, 15,125,823
product rows, 21,491 partitions, 4,181 gap artifacts, 1,901,665 unjoinable source rows,
47,279,134 physical source rows. Row equation: 47,279,134 = 45,377,469 + 1,901,665.
All 102,740 descriptor-referenced partitions and lineages verified: contained regular-file
paths, hashes, actual frozen Arrow schemas, row counts, descriptor sums, exact
source-reference/ordinal bindings, no unreferenced artifact or staging file. Both
`.staging/` directories empty; sole completion per product. Post-run available bytes:
221,671,538,688. The accepted generation-0 authority was not altered; nothing was downloaded.

Record 475 is published. Both actor fields return to the Lead Quantitative Finance
Researcher/Engineer. Gate 2 remains accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`;
next ticket remains `NONE`. No retry, wrapper, detach, polling loop, cleanup, second
invocation, source correction, other product, catalog transaction, NautilusTrader work,
experiment, model, Harmonic Trader repository work, PAPER, LIVE, or next-ticket work is
authorized.

Governing documents:

- research/sprint_004/475_CEX002_PRICE_STATE_INTEGRATION_AND_REAL_RUN_RECORD.md
- research/sprint_004/474_CEX002_FIXED_CLOSEOUT_AND_PRICE_STATE_SOURCE_AUTHORIZATION.md
- research/sprint_004/473_CEX002_REALIZED_FUNDING_ACCEPTANCE.md
- research/sprint_004/460_CEX002_HOURLY_KLINE_PRODUCT_ACCEPTANCE.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- docs/adr/0024-typed-normalization-and-partition-atomic-publication.md
- docs/adr/0025-complete-product-sizing-and-fee-authority.md
- docs/adr/0026-non-backdated-fee-scenarios.md
- docs/engineering/DEVELOPMENT_ROLES.md
- tickets/CEX-002.md
