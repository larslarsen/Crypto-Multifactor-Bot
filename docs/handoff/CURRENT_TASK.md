# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority execution
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Governing documents:

- tickets/CEX-002.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- research/sprint_004/59_CEX001_SOURCE_AND_PLATFORM_REVIEW.md
- research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md
- research/sprint_004/61_CEX002_SPARK_SOURCE_REVIEW.md
- research/sprint_004/63_CEX002_GROK_SOURCE_REVIEW.md
- research/sprint_004/64_CEX002_GROK_SECOND_SOURCE_REVIEW.md
- research/sprint_004/65_CEX002_CLAUDE_SOURCE_REVIEW.md
- research/sprint_004/66_CEX002_GATE1_EXECUTION.md
- research/sprint_004/67_CEX002_GATE1_EXECUTION_REVIEW.md
- research/sprint_004/68_CEX002_CLAUDE_OPERATIONAL_SOURCE_REVIEW.md
- research/sprint_004/69_CEX002_CLAUDE_CHECKPOINT_SOURCE_REVIEW.md
- research/sprint_004/70_CEX002_CLAUDE_FINAL_SOURCE_REVIEW.md
- research/sprint_004/71_CEX002_GATE1_RESUMABLE_EXECUTION.md
- research/sprint_004/72_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md
- research/sprint_004/73_CEX002_CLAUDE_TEST_SOURCE_REVIEW.md
- research/sprint_004/74_CEX002_GATE1_RESUMABLE_EXECUTION.md
- research/sprint_004/75_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md
- research/sprint_004/76_CEX002_CLAUDE_AUTHORITY_PLAN_SOURCE_REVIEW.md
- research/sprint_004/77_CEX002_CLAUDE_DURABLE_AUTHORITY_SOURCE_REVIEW.md
- research/sprint_004/78_CEX002_CLAUDE_STABLE_AUTHORITY_SOURCE_REVIEW.md
- research/sprint_004/79_CEX002_CLAUDE_TRANSITION_SOURCE_REVIEW.md
- research/sprint_004/80_CEX002_GROK_TRANSITION_SOURCE_REVIEW.md
- research/sprint_004/81_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md
- research/sprint_004/82_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/83_CEX002_SPARK_TEST_SOURCE_REVIEW.md
- research/sprint_004/84_CEX002_SPARK_FINAL_TEST_SOURCE_REVIEW.md
- research/sprint_004/85_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md
- research/sprint_004/86_CEX002_TRUNCATED_TEST_SUITE_REVIEW.md
- research/sprint_004/87_CEX002_GROK_RESTORED_TEST_SOURCE_REVIEW.md
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

## First Grok corrective source review

Grok's rewrite closes most review-61 defects, but source inspection rejects three residual
source-authority failures at the exact hashes in review 63. The supplied headerless metrics
fixture is still classified as field names; aggregate family counts still promote a product
to official completeness when a discovered symbol has zero objects; and Coinalyze can
qualify BTC responses for an ETH-only request while reporting a schema path instead of the
actual liquidation/OI unit. The bounded real Coinalyze responses also need redacted content
hash/retrieval provenance in the qualification evidence.

Grok executed tests despite the explicit role prohibition. Those results are disregarded;
Hermes remains the only integration and command-execution actor.

## Second Grok correction authorization

If committed `HEAD` does not yet contain review 63 plus this section and the matching
ticket section, Jr Dev — Hermes must first publish only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/63_CEX002_GROK_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Jr runs only `python3 scripts/check_repo_control.py` and `git diff --check`, excludes all
source/test drops and unrelated dirty paths, pushes, and establishes
`HEAD == origin/main`. Once that committed branch state exists, Sr Dev — Grok Build on
Grok 4.6 High is automatically authorized for the surgical correction in review 63; no
ephemeral prompt, owner-supplied source hashes, or further handoff edit is required.

The correction is confined to the three reviewed Python paths and existing fixture
directory. It must preserve the accepted rewrite, add failing-then-passing focused tests
for the three direct probes, and add redacted Coinalyze response provenance. Grok performs
no test execution, network run, integration, record edit, Git operation, commit, push,
purchase, catalog mutation, or publication. It stops for source review with exact hashes.
Jr integration remains unauthorized.

## Second Grok corrective source review

The second Grok patch closes metrics schema identity, Coinalyze requested/returned symbol
checking, actual unit reporting, and empty listed-prefix detection. Review 64 rejects two
remaining semantic defects and one test-source defect: a universe symbol absent from a
product family is still omitted and can be silently promoted; reported Coinalyze
provenance hashes reconstructed JSON rather than retained raw responses; and the new
mismatch test expects a different error from the correct implemented failure.

Grok 4.6 High has now required two rejected corrective reviews on this source-authority
task. The next bounded correction is routed to Sr Dev — Claude Build using Claude Opus 5.

## Claude review-publication transition

If committed `HEAD` does not yet contain review 64, the Claude senior-role addition, this
section, and the matching ticket section, Jr Dev — Hermes must first publish only:

- `AGENTS.md`;
- `docs/engineering/DEVELOPMENT_ROLES.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/64_CEX002_GROK_SECOND_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Jr runs only `python3 scripts/check_repo_control.py` and `git diff --check`, excludes all
source/test drops and unrelated dirty paths, pushes, and establishes
`HEAD == origin/main`. Once that committed state exists, Sr Dev — Claude Build on Claude
Opus 5 is automatically authorized for the surgical correction in review 64; no ephemeral
prompt, owner-supplied source hashes, or further handoff edit is required.

## Claude corrective source acceptance

Review 65 accepts Claude's source-only correction at exact hashes. Full-universe missing
family prefixes now become typed blocking evidence; Coinalyze provenance now identifies
and rehashes retained raw response bytes; and the focused mismatch test contract is
correct. This is the first accepted Claude Build source review and is positive
project-specific routing evidence, pending Hermes integration.

Jr Dev — Hermes is authorized to perform only the integration, command sequence, two real
Gate 1 qualification/resume runs, evidence record, commit, and push specified verbatim in
review 65. The key must be loaded only from `.env` into `COINALYZE_API_KEY`, never printed
or placed in command arguments. Exit 2 is preserved as honest blocked-matrix evidence, not
reported as success. Exit 1 stops the run. Interrupted work resumes the same store and
progress file. The execution record path is
`research/sprint_004/66_CEX002_GATE1_EXECUTION.md`.

For this intermediate Gate 1 integration, Hermes runs the focused CEX-002 suite and the
directly depended-on atomic-download suite specified in review 65. The already attempted
full-suite failures in excluded dirty DEX/BitMEX drops are recorded as nonblocking
environmental evidence. No `-k` substitute or clean-worktree rerun is authorized. The
unchanged full suite remains mandatory once at final CEX-002 release acceptance.

## Claude operational-correction source review

Claude's first review-67 correction is rejected at the exact hashes in review 68. The
patch establishes the right architecture, but direct probes prove that cross-request
listing-page substitution and mismatched provider-checksum checkpoints are accepted,
malformed checkpoints silently restart empty, and the preflight budget counts one unique
object multiple times across regime aliases. Retry incidents are not durable across an
abort, retry ownership can nest, and the required abort/resume test is absent. Jr
integration and another real run remain unauthorized.

Hermes must first publish only this file, review 68, and `tickets/CEX-002.md`, excluding
the rejected source/test drop and every unrelated dirty path. Once that record is committed
and pushed, Sr Dev — Claude Build on Claude Opus 5 is automatically authorized for the
surgical correction in review 68. No ephemeral developer prompt is required.

## Gate 1 real-execution review

Review 75 accepts Hermes's integration discipline but rejects Gate 1 evidence. Both real
runs honestly blocked and the store resumed, but the archive-name union was promoted into
an unproved perpetual universe, the 256 MiB allowance reset across invocations, semantic
sample identity changed, source qualification was conflated with temporal completeness,
and the report exposed a multi-terabyte raw requirement without a deduplicated physical
storage/shortfall decision.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the source/test correction
specified in review 75. It must establish affirmative official membership evidence,
immutable cumulative planning, physical storage feasibility evidence, separated source and
coverage states, and stable Coinalyze anchors. It performs no tests, network/data run,
integration, records, Git, purchase, deletion, catalog mutation, Gate 2, or Harmonic Trader
work and stops for source review with exact hashes. Hermes and every real rerun remain
unauthorized.

## Claude review-75 source review

Review 76 rejects Claude's first review-75 correction while retaining its membership,
coverage-state, Coinalyze-anchor, physical-storage, plan-lock, and cumulative-ledger
direction. The residual blockers are a crash window between sample checkpoint and ledger
write, unauthenticated retained FAPI rows, unstable/incomplete plan input identities,
unverified storage credit, unsupported temporal-gap explanations, and truncated Coinalyze
product gaps.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the surgical nine-path
source/test/fixture correction in review 76. It performs no tests, network/data run,
integration, records, Git, purchase, deletion, catalog mutation, Gate 2, Nautilus, or
Harmonic Trader work and stops for source review with exact hashes. Hermes remains
unauthorized.

## Claude review-76 source review

Review 77 accepts the crash-safe reservation, legacy range, plan-validation, storage,
temporal-gap, and complete-gap closures but rejects the source before integration. The
remaining failures are confined to raw/parsed exchangeInfo binding and value validation,
full re-proved plan authority inputs, persisted-ledger validation, and native identity for
the complete Coinalyze support map.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the final two-path source
and test-source correction in review 77. It performs no tests, network/data run,
integration, fixtures, records, Git, purchase, deletion, catalog mutation, Gate 2,
Nautilus, or Harmonic Trader work and stops for source review with exact hashes. Hermes
remains unauthorized.

## Claude review-77 source review

Review 78 accepts inseparable raw exchangeInfo parsing, re-proved listing/retained plan
inputs, and full Coinalyze native identity. The source still cannot resume live because
volatile response SHA/server time are plan inputs; unknown nonempty contract semantics can
qualify; and reduced positive or zero persisted ledger amounts restore allowance.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the two-path correction
in review 78. It performs no tests, network/data run, integration, fixtures, records, Git,
purchase, deletion, catalog mutation, Gate 2, Nautilus, or Harmonic Trader work and stops
for source review with exact hashes. Hermes remains unauthorized.

## Claude review-78 source review

Review 79 accepts the stable semantic/provenance split, fail-closed contract semantics,
and structured ledger direction, but rejects two residual transition defects. A changed
live authority response is durably written before the immutable plan rejects it and can
poison later valid resumes. The in-memory acquisition path fetches a raw payload before
declaring a content-address reuse, then records the transfer as zero-byte no-transfer.

At the owner's direction, Sr Dev — Grok Build using Grok 4.6 High is authorized only for
the two-path correction in review 79 because Claude is unavailable. Grok performs no
tests, network/data run, integration, fixtures, records, Git, purchase, deletion, catalog
mutation, Gate 2, Nautilus, or Harmonic Trader work and stops for source review with exact
hashes. Hermes remains unauthorized.

## Grok review-79 source review

Review 80 accepts Grok's two-path correction. Live authority and first-closed evidence are
now staged until the immutable plan accepts them, so a rejected response cannot poison
durable metadata. Content-address reuse is proved before raw retrieval; an actual raw
fetch is always recorded as transferred. Focused source tests cover both corrections.

Hermes is authorized only for the nine-path accumulated CEX-002 integration, focused
commands, preserved-store two-run qualification/resume, evidence record 81, commit, and
push specified in review 80. Exit 2 remains honest blocked evidence, not success. Exit 1
stops further network work. The full suite remains deferred to final release acceptance.

## Focused integration failure review

Review 82 accepts Hermes's stop and retains review 80's production acceptance. All five
failures are stale or internally inconsistent test contracts: current-unarchived gap
precedence, typed temporal coverage, an incomplete oversized-source fixture, immutable
plan history, and a row-validation test missing its authenticated envelope.

Codex Spark is authorized only for the one-path mechanical test-source correction in
review 82. It performs no tests, production/fixture edit, integration, records, Git,
network/data run, Gate 2, Nautilus, or Harmonic Trader work and stops for source review
with the exact test hash. Hermes remains unauthorized.

## First Spark test-source review

Review 83 accepts three corrections but rejects two residual test defects. The oversized
fixture still lacks affirmative current-perpetual membership, and the immutable-plan test
retains the same rewritten retained/new byte expectations that originally failed.

Spark is authorized only for the two exact one-file test corrections in review 83. It
performs no tests, production/fixture edit, integration, records, Git, network/data run,
Gate 2, Nautilus, or Harmonic Trader work and stops for review with the exact test hash.
Hermes remains unauthorized.

## Final Spark test-source review

Review 84 accepts Spark's one-file correction. All five stale focused tests now express
the accepted current-unarchived, typed-coverage, complete-fixture, immutable-plan, and
authenticated-envelope contracts, and the intermediate unused assignment is removed.

Hermes is authorized only for the nine-path integration, full focused command sequence,
preserved-store two-run qualification/resume, evidence record 85, commit, and push
specified in review 84. Exit 2 remains honest blocked evidence; exit 1 stops network work.
Gate 2, Nautilus, and model work remain unauthorized.

## Focused lint failure review

Review 86 accepts Hermes's stop but supersedes review 84's test acceptance. The 51 unused
imports are evidence that Spark overwrote the accumulated roughly 3,600-line suite with a
correction based on the older committed test file, deleting the review-75 through
review-79 coverage. The passing 84-case result is therefore incomplete. Production
acceptance remains unchanged.

Grok is authorized only to restore the deleted test sections in the single test path from
the governing reviews. It performs no tests, production/fixture edit, integration,
records, Git, network/data run, Gate 2, Nautilus, or Harmonic Trader work and stops for
review with the exact hash and test-function count. Hermes remains unauthorized.

## Stop condition

The only active authorization is Hermes's command and real execution in review 87. The
accepted nine-path drop is committed. The existing store, legacy plan, checkpoints,
reports, and over-budget retained
evidence must be preserved. CEX-002 remains `IN_PROGRESS`; Gate 2, every other ticket,
Nautilus integration, and model work remain unauthorized; next ticket remains `NONE`.

## Grok restored test-source review

Review 87 accepts the restored 3,669-line, 135-function test source. Every deleted
review-75 through review-79 section is present, Spark's five corrections remain, and no
duplicate test names were found. Production acceptance is unchanged.

At the owner's explicit direction, the reviewer commits and pushes the exact accepted
nine-path drop with review 87. Hermes then runs only the focused commands and
preserved-store execution. Failures are corrected forward; no restore, reset, checkout,
stash, clean, or discard is authorized. Gate 2, Nautilus, and model work remain
unauthorized.
