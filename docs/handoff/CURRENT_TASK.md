# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev — Hermes — publish the reviewer data-destination correction only
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

## Jr governance-publication boundary

Jr Dev — Hermes must commit and push only:

- `AGENTS.md`;
- `docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md`;
- `docs/engineering/DEVELOPMENT_ROLES.md`;
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/59_CEX001_SOURCE_AND_PLATFORM_REVIEW.md`;
- `research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md`;
- `tickets/CEX-001.md`; and
- `tickets/CEX-002.md`.

Exclude every production/test source drop, `opencode.json`, DEX path, database sidecar,
generated artifact, and unrelated path. Run only `python3 scripts/check_repo_control.py`
and `git diff --check` for this governance publication. Jr owns Git, commit, and push and
must report the pushed commit plus exact `HEAD == origin/main`. Jr performs no source
integration, test suite, network call, catalog mutation, purchase, or data publication.

## First implementation authorization after publication

Only after Jr publishes the governance correction and proves `HEAD == origin/main`,
Implementation Dev — Codex Spark may author the bounded CEX-002 Gate 1 inventory,
Coinalyze-client, secret-redaction, schema-sampling, storage-accounting, report plumbing,
and corresponding test source specified under CEX-002's authorized first drop.

Codex Spark performs no network run, integration, repository-record edit, Git operation,
commit, push, purchase, or publication and stops for fresh reviewer source inspection with
exact hashes. Jr integration and test execution are not pre-authorized. Senior semantic,
authority, atomicity, and corrective source work is not yet authorized.

## Stop condition

The immediate stop is after Jr publishes these nine control-plane records. CEX-002 remains
`IN_PROGRESS`; next ticket remains `NONE`.
