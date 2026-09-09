# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
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

Batch B integration and the single local run are complete: integration
`f83653c8747e627d9e8ceb2b88973e16556602f3`, completion
`dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f`, exit 0. The normalizer ran
once in the foreground starting 2026-09-09T02:48:55Z UTC (2026-09-08T19:48:55 PDT) for 297.4 seconds.
Reviewer audit of every output file/schema/hash/raw value/ordinal/gap and all 18 comparisons
passed (two reviewer-authored read-only scripts executed by Hermes, exit 0). Logical output is
136,197,937 bytes; actual allocation ceiling is 187,270,569 bytes. A file equation of
2*16,373 + 2*2,570 + 2 + 1 + 1 = 37,890 files was verified; staging is empty; sole completion.

During read-only exploration after the run, an invented `data/.cex002_liquidation_observed_daily/d/`
listing exited 2 (directory does not exist). This evidence-workflow error was recorded honestly
without patch, retry, or cleanup. Hermes's interactive approval timeout subsequently blocked a
read-only Python inspection command; the reviewer stopped the session and the owner renewed
permission via `continue`. Resume was read-only only: no tests, integration, or normalizer rerun.
Record 477 published with full reconciliation evidence; both actor fields return to the reviewer.
Liquidation-data acceptance remains pending with the reviewer; CEX-002 stays IN_PROGRESS,
seven products accepted. Record 477 completion hash:
`dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f`.

The source acceptance and original integration/run contract below remain the audit trail.

Review 476 accepts the complete Batch B source drop after consolidated correction and a
fixture-only repair. All 46 focused tests passed under the targeted senior exception. The
reviewer independently reproved these final source identities:

- `src/cryptofactors/ingest/binance_usdm_liquidation_observed.py`;
- `scripts/research/normalize_binance_usdm_liquidation_observed.py`; and
- `tests/ingest/test_binance_usdm_liquidation_observed.py`.

Production SHA-256: `2e001f2d63c6f127d58e7db0c071a2971ecb6a769d5bd1d85b322d085a1ee257`
(1,491 lines); CLI: `8d97b52138c1ff27a39ddcc5b3fbb99f7db774ba5d0c948103d9d9b95830cfee`
(54 lines); tests: `e4949ec6d654cac65f29c976ec13429fa225843545c21571f2725dd1f08d0024`
(1,033 lines). Sol is finished and all three paths are frozen.

All 569 liquidation responses and their inventory are already local. The drop preserves the
existing 15-column observed/censored schema, exact base-asset amounts and imbalance, full native
mapping/lineage, missing/unmapped gaps and immutable publication. It also produces the bounded
comparison evidence from the three retained Coinalyze overlap responses and accepted official
bar/OI/funding products. Review 476 fixes dates, fields, unit conversion and explicit missing
ETH OI overlap. No source substitution or new acquisition is needed for this source assignment.

The assigned actor is Hermes, directly prompted by the reviewer under the owner's instruction,
using the currently free Nous Portal model `poolside/laguna-s-2.1:free` for this bounded assignment.
Review 476's complete Hermes workflow governs: exact
preproof and ordered checks, three-path integration commit/push, capacity and authority preproof,
one foreground local run into `data/.cex002_liquidation_observed_daily` with at least 7,200 seconds
available, independent artifact/row/gap/18-comparison reconciliation, and terminal Record 477
publication with both actor fields returned to the reviewer. Execute the successful sequence
without intermediate approval handoffs. Stop at the first nonzero command or failed proof and
publish the exact terminal evidence without patch/retry/cleanup. No acquisition, accepted-product
rerun, catalog publication or later batch is authorized. Source acceptance leaves seven data
products accepted; liquidation data and Gate 4 still await the reviewer.

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
