# CEX-002 Retained-Authority Source Acceptance and Integration

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** corrected two-file source accepted for exact integration and focused validation
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Accepted source

The reviewer inspected Grok's review-325 continuation once without executing source, tests,
Ruff, control, planning, acquisition, or data commands:

| Path | Accepted SHA-256 | Lines |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` | 11,125 |
| `tests/acquisition/test_binance_usdm_harmonic_acquisition.py` | `19165d4e5d3fef565f4f35c41c7bf82322ad60eaa453dcd97cd41ef93354ed96` | 5,673 |

The test source has 203 test functions. The CLI is unchanged at SHA-256
`6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`. Only the two
authorized paths changed among CEX-002 source/test/CLI paths; unrelated dirty work remains
outside this review.

Review 326 accepts the source/test drop as the complete ADR-0030 correction:

- the already pinned receipt 258 is decoded and its exact retained-credit and report-summary
  field sets, scalar types, source, rejected-row facts, lineage digest/count, and zero
  coefficient-only state are authenticated;
- the receipt's sorted 73-key set, never a progress intersection or hard-coded list, drives
  both plan passes and retained adoption;
- planning re-proves exact progress/raw/sidecar bindings, exact positive byte types, unique
  content, plan membership, 73 objects, 5,225,416 bytes, 68 selected keys, and 5 cost keys;
- all other complete progress objects are planned unretained and acquired normally;
- the corrected plan receipt is explicit schema v2 under an ADR-0029-plus-ADR-0030 v2 policy,
  compactly binds the retained key-set digest/decomposition, and reauthenticates those values
  against persisted pins on every chain replay;
- the production-shaped regression proves 90 progress intersections, exactly 73 retained
  plan/completion rows, 17 checksum-verified downloads, and 34 official object/sidecar calls;
  and
- receipt, summary, lineage, digest, count, byte, placement, alias, exact-type, compact-replay,
  and incompatible semantic-plan boundaries are covered with bounded synthetic tests.

The accepted correction changes code and semantic plan identity. It does not authorize
corrected code to open the rejected real store. ADR-0030 retirement and replanning remain
separate operations after integrated validation is reviewed.

## Hermes integration and validation

Hermes owns one exact integration and focused validation round. Preserve every unrelated
modified or untracked path. Do not open, inspect through the acquisition module, rename,
delete, finalize, or otherwise touch `data/cex002_qualify/gate2` or create
`gate2_retired`.

Preproof must establish:

- synchronized `HEAD == origin/main`, with review 326 and review-325 commit
  `4b322663e4e5cfbe02338e73f3aed320ac83e847` in ancestry;
- the exact accepted source, test, and unchanged CLI hashes above;
- exactly the accepted source and test are modified among those three paths;
- no staged path; and
- `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, ADR-0030, reviews 324-326, and the
  CLI are clean.

Any failed preproof stops without repair, reset, restore, checkout, stash, staging, test, or
rerun. On success:

1. stage only the accepted source and test;
2. prove the exact two-path cached set and run `git diff --cached --check`;
3. commit with message `integrate CEX-002 exact retained authority correction` and push
   `main`;
4. run the focused Ruff command exactly once; and
5. only if Ruff passes, run the targeted acquisition pytest command exactly once.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py \
  scripts/research/acquire_binance_usdm_harmonic_release.py \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

On any nonzero result or timeout, stop without repair, rerun, later command, evidence edit, or
Git mutation and return the exact first failure. Do not route a source correction yourself.

Only after both commands pass, create exactly:

- `research/sprint_004/327_CEX002_RETAINED_AUTHORITY_INTEGRATION_AND_VALIDATION.md`

Record the integration commit, exact hashes/line/function counts, exact commands, UTC
start/end/elapsed/status/output summaries, and unchanged real-store prohibition. Stage only
record 327, prove the cached path and cached diff, commit with message
`record CEX-002 retained authority validation`, push `main`, run the ticket's shared-tree
`git diff --check` exactly once, and stop for review.

Do not run full-suite pytest, repository-wide Ruff, control, `plan`, `acquire`, `verify`,
qualification, sizing, capacity, network, or data commands. Do not retire or mutate the old
store. Old-store retirement, corrected real planning, acquisition, replay, terminal
verification, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiments,
PAPER/LIVE, and next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next
ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
