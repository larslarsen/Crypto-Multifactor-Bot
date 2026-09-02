# CEX-002 Review 465 - Membership Product Acceptance

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the corrected integration and `binance_usdm_perpetual_membership` product
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - four of eleven required products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Decision

The reviewer accepts integration commit `d2753e7e5996fbe1acc2825d3399c5f64d529573`, Hermes
publication commit `1567d14403cd0ecb0e1b89b358f2ad43b550e730`, and the exact
descriptor-referenced `binance_usdm_perpetual_membership` product.

The integration commit contains exactly the three Review-463 developer paths. All 27 focused tests,
targeted Ruff, and repository control passed before integration. The one foreground real command
exited zero in about five seconds. The completion descriptor authenticates the three pinned
authorities and the accepted normalizer, binds the frozen schema, and reconciles exactly 1,008
classifications minus 237 exclusions to 771 membership rows. The 771 rows split into 698 detailed
metadata identities and 73 funding-only identities. All 771 partition and 771 lineage digests were
verified against content-addressed filenames with zero mismatches; staging is empty and exactly one
completion exists.

Accepted product identity:

- completion SHA-256:
  `01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3`;
- schema SHA-256:
  `35c7101271c80c3c6faa222b57e5ff7a48930a470aebbc2cf330dee43c39fafb`;
- normalizer source SHA-256:
  `7e14254cd8275521a52ab88faf747f9c72fd0fd51cc2a7d97d4f405af723ffc4`;
- 771 rows, 771 Parquet partitions, and 771 lineage documents; and
- 5,285,816 partition bytes plus 777,292 lineage bytes.

Record 464 contains one clerical preproof typo: it gives the CLI SHA-256 as
`cd762f2b673bc2beca322da6a8ae6358d51f99cfe819ebf6313f330414140bd`. The accepted Review-463
identity, working-tree file, and integration-commit blob all independently equal the correct
64-character SHA-256
`cd762f2b673bc2beca322da61a8ae6358d51f99cfe819ebf6313f330414140bd`. This review supersedes
the missing `1` in Record 464; no source, test, CLI, output, or rerun is required.

Record 464 also describes four products as already accepted before reviewer disposition. Hermes
reported and published the implementation outcome but is not an acceptance authority. This review
is the exclusive acceptance of the fourth product.

## Boundary

Four of eleven required products are now accepted: membership, hourly bars, hourly trade flow, and
five-minute open interest. Gate 3 remains `IN_PROGRESS`; realized funding, indicative funding,
mark/index/basis, observed liquidation, cost calibration, the coverage/gap product, the final
bundle, Gate-4 reconciliation, Gate-5 catalog loading, and CEX-002 acceptance remain outstanding.

No rerun, replay, source change, data mutation, cleanup, next product, catalog transaction,
NautilusTrader check, experiment, model, Harmonic Trader, PAPER, LIVE, or next ticket is authorized
by this review. Both actor fields remain with the reviewer pending selection of the next smallest
bounded CEX-002 product.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/465_CEX002_MEMBERSHIP_PRODUCT_ACCEPTANCE.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All source, test, data, runner, acceptance-command, and unrelated dirty paths remain unstaged and
untouched.
