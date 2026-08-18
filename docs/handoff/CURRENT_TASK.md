# CURRENT_TASK

Ticket: CEX-001
State: IN_PROGRESS
Next required actor: Jr Dev — Hermes — publish the CEX strategic pivot and first-source-drop authorization
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Governing documents:

- tickets/CEX-001.md
- docs/adr/0016-cex-first-full-derivatives-research-spine.md
- research/sprint_004/54_CEX_SPINE_GAP_AUDIT.md
- docs/engineering/DEVELOPMENT_ROLES.md

## Decision

DEX-003 is `SUPERSEDED`, not accepted. Its remaining acquisition/publication gates are
unfinished and the previously authorized twenty-fourth Grok correction is withdrawn.
Preserve all DEX source drops, databases, raw evidence, reports, and published artifacts;
perform no further DEX edits, integration, migrations, tests, RPC work, publication, or
model work.

DATA-009 is also `SUPERSEDED`, not accepted. Its 45-symbol `bitmex_funding_full`
publication is the largest of the five all-zero/empty-interval artifacts and remains
preserved only as rejection evidence pending CEX-001 quarantine.

CEX-001 is the sole active ticket. It delivers a full Binance USD-M linear-perpetual
research spine across every historically listed contract in the declared coverage—not a
fixed 20/50/100-name panel. Required aligned products are contract versions, trades,
one-minute bars, BBO/fixed depth, OI, realized funding, liquidations, mark/index/basis,
effective fee schedules, typed gaps, a pinned bundle descriptor, and a clean consumer
harness. No individual parser, sample, report, or subset completes the ticket.

No harmonic-model development, payoff analysis, holdout inspection, PAPER promotion, or
LIVE work is authorized.

## Evidence establishing the pivot

- DATA-011 is an accepted but limited 23-instrument Binance spot daily-bar panel.
- The Bybit implementation is a local public-trade-archive normalizer; it is not a
  production historical microstructure bundle.
- No production CEX OI, liquidation, order-book/BBO, basis, or aligned-bundle pipeline is
  present.
- All five retained BitMEX funding parquet artifacts are invalid: 307,738 total rows,
  zero nonzero funding rates, and 307,738 empty funding intervals, while cataloged
  `PASS / REGISTERED`.
- The source converts missing funding rates to `0.0`, accepts empty intervals, and the
  backfill publisher unconditionally assigns `PASS` to any non-empty merged table.

The exact dataset IDs, counts, catalog states, and source findings are recorded in
`research/sprint_004/54_CEX_SPINE_GAP_AUDIT.md`.

## Jr publication boundary

Jr Dev — Hermes must commit and push only the reviewer-owned control-plane pivot:

- `docs/adr/0016-cex-first-full-derivatives-research-spine.md`;
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/54_CEX_SPINE_GAP_AUDIT.md`;
- `tickets/CEX-001.md`;
- `tickets/DATA-009.md`; and
- `tickets/DEX-003.md`.

Exclude `opencode.json`, every DEX production/test/migration/script source drop, the two
untracked DEX research drafts, databases, logs, generated data, and every unrelated path.
Run `python3 scripts/check_repo_control.py` and `git diff --check` for this governance-only
publication. Jr owns Git, commit, and push, then reports the pushed commit and exact
`HEAD == origin/main` state. Jr performs no source integration, test suite, network call,
catalog mutation, data purchase, or data publication in this step.

## First Sr source authorization after publication

Only after the governance commit is pushed and `HEAD == origin/main`, Sr Dev — Grok Build
may author Gate 0 and Gate 1 production/test source exactly as specified in CEX-001:

1. atomic/idempotent quarantine machinery for the five exact invalid BitMEX dataset IDs,
   preserving parquet/manifests and proving resolver exclusion/rollback;
2. fail-closed BitMEX normalizer/backfill corrections for missing, invalid, empty,
   all-zero, drifted, errored, or incomplete funding evidence; and
3. a resumable content-addressed real-source qualification runner for the complete
   historical Binance USD-M perpetual family and every required CEX product, producing
   the source/procurement/storage matrix without purchase or fixed-N scope.

Sr authors production and test source only. Sr runs no tests or network, edits no records,
performs no integration/catalog mutation/Git/commit/push, and stops for fresh reviewer
source inspection with exact hashes. No Jr integration is pre-authorized.

## Source and cost policy

Official Binance archives/APIs are preferred where complete and checksummed. Historical
microstructure products may require a licensed capture source. Real samples must establish
schema, full-family coverage, incidents/revisions, availability semantics, licensing,
storage, acquisition method, and official-source overlap before an external purchase.
The owner must approve the recorded price. If the complete source cannot be obtained, the
ticket becomes honestly blocked; it does not shrink the universe or manufacture data.

## Stop condition

The immediate stop is after Jr publishes these seven records. CEX-001 remains
`IN_PROGRESS`; next ticket remains `NONE`.
