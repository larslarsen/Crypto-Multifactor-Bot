# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev — Grok Build — author the bounded CEX-002 Gate 1 corrective source drop
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Governing documents:

- tickets/CEX-002.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- research/sprint_004/59_CEX001_SOURCE_AND_PLATFORM_REVIEW.md
- research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md
- research/sprint_004/61_CEX002_SPARK_SOURCE_REVIEW.md
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

## Spark source review

Spark delivered a final four-path drop at the exact hashes recorded in review 61. Source
inspection rejects it before Jr integration. Direct probes prove headerless numeric data
is still accepted as a schema and tampered content-addressed bytes are trusted on resume.
The Coinalyze client is fabricated receipt plumbing over nonexistent endpoints rather than
a real source client, S3 pagination remains invalid, an unproved 64 MiB cap remains, and
the matrix can both silently promote partial sources and remain permanently blocked by
derived outputs. Exact findings are in review 61.

The earlier transient write under the preserved CEX-001 paths is a provenance breach. The
final reviewed drop is now in the authorized non-colliding paths, but the original rejected
CEX-001 source bytes recorded in review 59 are no longer present at those old paths. Do not
claim they were preserved or restored.

## Review-publication transition

If committed `HEAD` does not yet contain review 61 plus the Grok designation in both this
file and `tickets/CEX-002.md`, Jr Dev — Hermes must publish only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/61_CEX002_SPARK_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Jr runs only `python3 scripts/check_repo_control.py` and `git diff --check`, excludes every
source/test drop and unrelated dirty path, pushes, and establishes `HEAD == origin/main`.
Once the committed branch contains all three records, the Grok authorization below becomes
active automatically; no further handoff edit or owner-supplied source hash is required.

## Grok corrective source authorization

Sr Dev — Grok Build, using Grok 4.6 High, may replace only the final reviewed CEX-002
source/test paths and fixture directory recorded in review 61. The correction must close
all fifteen findings in that record, including:

- real Coinalyze history endpoints, query contract, response parsing, source samples,
  retention/unit evidence, overlap-reconciliation inputs, and environment-only secret use;
- correct S3 ListObjectsV2 pagination and exact one-minute interval selection;
- known per-family header/headerless schemas backed by real-shaped fixtures;
- checksum-required, rehashed resume with no unproved object-size cap;
- complete-family/symbol/incident-aware authority with no quote-label promotion;
- source-gate treatment that does not block on derived outputs;
- available `bookDepth` plus `bookTicker` cost inventory;
- authenticated current-contract comparison and explicit historical-perpetual rule; and
- nonzero default exit for incomplete required source coverage.

Grok authors source and test source only. It performs no network run, test execution,
integration, repository-record edit, Git operation, commit, push, purchase, catalog
mutation, or publication and stops for fresh reviewer source inspection with exact hashes.
Jr integration remains unauthorized.

## Stop condition

Grok stops after delivering the bounded corrective source/test-source drop and exact
SHA-256 hashes for every changed path. CEX-002 remains `IN_PROGRESS`; next ticket remains
`NONE`.
