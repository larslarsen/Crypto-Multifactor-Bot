# CEX-002 Review 445 — Open Interest Product Acceptance

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept corrected terminal evidence and the `binance_usdm_open_interest_5m` product
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Acceptance

Hermes commit `c6338e5f1c39e1a144d79de21e79b111c3142493` changed exactly Record 444,
CURRENT_TASK, and CEX-002; it is pushed with `HEAD == origin/main`. Repository control and the
restricted commit whitespace check pass.

Record 444 corrects Record 442's timezone and runtime claims, distinguishes descriptor publication
from unavailable supervisor exit status, reconciles all 19,744 lineage documents to 75,255
byte-identical repeated rows and 2,818 excluded adjacent-midnight spillovers, and proves all 181
pre-existing content-addressed partition/lineage pairs remain descriptor-referenced and
digest-valid. The deterministic preserved-inventory aggregate digest is
`c88a346d3118b54006217ba1dcf422ad0f836b6ab18ddf4de1d11fff8665f57b`.

Together Records 442 and 444 prove:

- 160,226,578 authenticated physical source rows reconcile exactly to 160,148,505 product rows,
  75,255 collapsed identical repeats, and 2,818 excluded spillovers;
- all 19,744 Parquet partitions and all 19,744 lineage documents match the completion descriptor;
- the quality-gap artifact contains 57,441 rows and the one authority-level typed gap is the fixed
  HBARUSDC 2026-07-09 provider checksum conflict;
- authority, schema, writer, artifact-byte, and staging facts satisfy Review 437; and
- no acquisition, replay, cleanup, second process, or silent gap removal occurred.

The completed `binance_usdm_open_interest_5m` product is accepted as a real Gate-3 component.
Gate 3 as a whole remains `IN_PROGRESS` because the other required CEX-002 products and later
reconciliation/release gates are not accepted by this review.

Record 444's header incorrectly labels its authoring actor as the Lead Quantitative Finance
Researcher/Engineer. Hermes authored and published Record 444; this review supersedes that clerical
label as `Jr Dev — Hermes`. Record 444 also omitted itself from CURRENT_TASK's governing-document
list; this review adds Records 444 and 445. The evidence and commit scope are unaffected.

No next product, source/test/CLI change, data command, acquisition, catalog transaction,
NautilusTrader check, experiment, backtest, model, trading-engine work, or next ticket is
authorized. The next required actor remains the reviewer and the next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/445_CEX002_OPEN_INTEREST_PRODUCT_ACCEPTANCE.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All implementation, data, runner, wrapper, and unrelated dirty paths remain unstaged and
untouched.
