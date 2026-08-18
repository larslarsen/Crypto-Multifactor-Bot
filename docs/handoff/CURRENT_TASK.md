# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Implementation Dev — Codex Spark — author the bounded CEX-002 Gate 1 source drop
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Governing documents:

- tickets/CEX-002.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- research/sprint_004/59_CEX001_SOURCE_AND_PLATFORM_REVIEW.md
- research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md
- docs/engineering/DEVELOPMENT_ROLES.md

## Decision

The destination is the complete real data needed by the original Harmonic Trader
geometry-plus-derivatives thesis before model development. CEX-002 replaces the overbuilt
CEX-001 contract and the rejected reduced price-only proof. It acquires every historically
observed Binance USD-M perpetual and publishes real trades/bars, OI, funding, basis,
observed liquidation flow, cost evidence, typed gaps, provenance, reconciliation,
resumability, a pinned bundle, and a clean NautilusTrader catalog-load check.

No fixed-N/current-listing universe, synthetic acceptance artifact, zero-filled missing
data, silent partial success, paid data purchase, historical-full-L2 prerequisite, DEX
work, harmonic-model development, payoff analysis, PAPER, or LIVE work is authorized.

## Why this reaches the target without Tardis

Official Binance archives/APIs supply the full-family trade/bar, five-minute OI/metrics,
realized funding, and mark/index/premium/basis inputs for free. Coinalyze's free API retains
daily long/short liquidation history indefinitely. Because Binance itself publishes at
most the latest liquidation per symbol per second, this field is explicitly an observed,
censored liquidation aggregate; no implementation may claim event completeness.

The original model needs terminal-leg OI change, funding state, and liquidation imbalance,
not full incremental historical L2. All available free Binance book/depth evidence is
still acquired for cost calibration, and live BBO/depth/liquidation/OI collection begins
prospectively under this ticket.

## Superseded work

- DEX-003 remains `SUPERSEDED`; preserve all its source drops, data, and evidence.
- CEX-001 is `SUPERSEDED`; preserve its rejected source drop without integration.
- The five invalid BitMEX funding artifacts remain preserved and must be quarantined under
  CEX-002 Gate 0 before any research consumer can resolve them.

## Published governance boundary

Jr Dev — Hermes published the nine-record data-destination correction at
`a0beb8687a03d09ea8479d98ccde5bf6b7cb9564`. Reviewer verification establishes:

- `HEAD == origin/main == a0beb8687a03d09ea8479d98ccde5bf6b7cb9564`;
- the CEX-002 governance publication precondition is satisfied; and
- the preserved dirty source drops and artifacts remain outside the published commit.

## Active first implementation authorization

### Publication transition rule

If the committed `HEAD` does not yet contain this section and the Spark designation in
both `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`, Jr Dev — Hermes must publish
only those two reviewer-prepared paths, run `python3 scripts/check_repo_control.py` and
`git diff --check`, push, and establish `HEAD == origin/main`. It must exclude every
production/test source drop and unrelated dirty path. Once the committed branch contains
both designations, the authorization below becomes active automatically and no further
handoff edit, owner-supplied hash, or reviewer chat instruction is required.

Implementation Dev — Codex Spark is now authorized against base commit
`a0beb8687a03d09ea8479d98ccde5bf6b7cb9564` to author the bounded CEX-002 Gate 1 inventory,
Coinalyze-client, secret-redaction, schema-sampling, storage-accounting, report plumbing,
and corresponding test source specified under CEX-002's authorized first drop.

The rejected CEX-001 files already present in the dirty working tree are preservation
evidence and must not be edited, deleted, renamed, imported, or treated as a starting
implementation. Spark's drop uses these non-colliding CEX-002 paths only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/` for bounded test
  fixtures only; and
- any minimal package export file strictly required to expose that new module.

Codex Spark performs no network run, integration, repository-record edit, Git operation,
commit, push, purchase, or publication and stops for fresh reviewer source inspection with
exact hashes. Jr integration and test execution are not pre-authorized. Senior semantic,
authority, atomicity, and corrective source work is not yet authorized.

## Stop condition

Spark stops after delivering the bounded source/test-source drop and exact SHA-256 hashes
for every changed path. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.
