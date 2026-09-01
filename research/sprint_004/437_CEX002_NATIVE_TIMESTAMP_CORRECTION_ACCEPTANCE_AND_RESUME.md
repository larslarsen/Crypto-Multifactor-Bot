# CEX-002 Review 437 — Native-Timestamp Correction Acceptance and Resume

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the exact two-path correction; authorize Hermes integration and one preserved-root resume
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted corrective drop

Static inspection accepts Review 436's exact two-path correction:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,577 | `c0de316be5a328875935feb9da03d49bb50a404b5d624c12813289b85f3e771b` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 800 | `aff38de6c41c1a66846cc76cfc1104c26bb628dd532cfbc1fdd0f8e1776f710d` |

The CLI remains 53 lines at SHA-256
`33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675`.

The production source now preserves every valid whole-second source timestamp without rounding or
clock-grid replacement. Actual elapsed seconds remain the product interval; stock and value changes
exist only across an exact 300-second interval not crossing a declared source gap. Complete missing
cadences are derived in the prior observation's phase and split safely at UTC-month boundaries.

The parser accepts at most the full-corpus maximum of 576 physical rows. Stable-sorted same-source
timestamp repeats collapse only when their complete raw CSV record bytes are identical, retain the
first physical ordinal as the economic row, and bind every collapsed ordinal in deterministic
partition lineage. Conflicting raw bytes and duplicate authority still fail. After this exact
collapse, the 288-economic-row ceiling remains enforced.

The filename contract-day remains authority. Exactly one fully valid immediately-adjacent next-day
row may be excluded only from next midnight plus 0 through 59 seconds and only when an owned row
remains. Its exact observed timestamp and raw identity remain in lineage. Every broader shape still
fails. Completion totals now reconcile every authenticated physical row to exactly one product,
spillover-exclusion, or identical-repeat outcome.

The new optional identical-repeat lineage field is omitted when empty. The 181 existing hidden
partition/lineage pairs precede the first affected repeat and remain byte-identical/reusable. The
Parquet schema, writer identity, CLI, authority loaders, accepted sizing source, and raw data are
unchanged.

Sol used its one authorized command exactly once. All 55 collected cases passed:

```text
.......................................................                  [100%]
```

The test source contains 32 test functions and covers the complete Review-436 acceptance and
rejection domain. Restricted whitespace inspection is clean. This targeted result is source-review
feedback; Hermes still owns integration validation, evidence, Git, and publication.

## Preserved resume state and capacity

`HEAD == origin/main == b20a5d53abc8636407e02a01451d854ee31dab07` before this review.
`data/.cex002_open_interest_5m` remains preserved with 181 Parquets plus 181 matching lineages,
empty staging, and no completion descriptor. No source review, scan, or test mutated that root.

The accepted sizing evidence projects 280,534,938 economic rows, 19,744 partitions, and
34,362,664,803 normalized bytes for this product. Review 436's complete archive proof gives a
lower exact expected equation if every economic field validates:

```text
160,226,578 authenticated physical rows
-    75,255 byte-identical repeated physical rows
-     2,818 adjacent-next-midnight spillover rows
= 160,148,505 product rows
```

The post-collapse per-source economic-row ceiling remains 288, so the accepted projection and its
partition/lineage allocation are not exceeded. The reviewer measured 99,645,513,728 available
bytes after the preserved partial output. Review 430's unchanged conservative requirement is
55,415,363,427 bytes, leaving 44,230,150,301 bytes beyond the equation. Hermes must recompute this
same equation immediately before launch and stop before mutation if it is insufficient.

## Hermes integration checks

Hermes first proves `HEAD == origin/main` at this review's publication commit, reproves the exact
three file identities above, and reproves the preserved hidden-root facts. It then runs in order,
stopping on the first nonzero result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/ingest/binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
```

After all four pass, Hermes stages exactly the accepted source and test paths, commits and pushes
them, and proves `HEAD == origin/main`. No control or evidence path belongs in the integration
commit. Hermes then recomputes capacity and launches only if the equation remains sufficient.

## One proven supervisor and resume

Hermes creates exactly one mode-0700 supervisor beneath one literal
`/tmp/cex002_oi_437_XXXXXX` directory. It uses Review 434's proven supervisor contract without a
repository wrapper:

1. set `REPO_ROOT=/home/lars/Crypto_Multifactor_Bot` and successfully `cd` there before recording or
   launching anything;
2. record the integrated source commit, exact command, canonical working directory, start/end UTC,
   shell and Python PID/start-tick pairs, stdout, stderr, and exit code inside that runner directory;
3. use the absolute interpreter and CLI paths below while retaining every authority and output
   argument as the accepted repository-relative string; and
4. launch once with `nohup setsid`, closed stdin, and all supervisor output inside the runner
   directory, then return after confirming one nonempty shell/Python identity pair.

The sole production command is:

```text
PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src
/home/lars/Crypto_Multifactor_Bot/.venv/bin/python
/home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py
--generation0-state data/cex002_qualify/gate2/state.sqlite
--generation0-content-root data/cex002_qualify/gate2/content
--v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz
--recovery-root data/cex002_recovery
--output-root data/.cex002_open_interest_5m
```

This resumes the same hidden root and downloads nothing. The untracked repository wrapper remains
forbidden. There is no foreground reproduction, cleanup, signal, retry, second wrapper, duplicate
runner, or replacement for any reason. Launch uncertainty is terminal. A live runner is monitored
only by its exact directory, PIDs, and Linux start ticks.

## Terminal evidence

At terminal, Hermes publishes
`research/sprint_004/438_CEX002_OPEN_INTEREST_NATIVE_TIMESTAMP_RESUME_RECORD.md`, updates CURRENT_TASK
and the ticket with both actor fields returned to the reviewer, stages exactly those three record
paths, commits, pushes, proves `HEAD == origin/main`, and stops. A terminal failure records the
complete captured logs and exact hidden-output facts without patch, cleanup, reproduction, or
retry.

On success record 438 additionally proves every descriptor-referenced file and digest, Parquet
metadata row totals, the three-part physical-row equation above, exact per-lineage spillover and
identical-repeat counts, all preserved prior artifact bytes, the fixed HBAR conflict, typed gaps,
authority counts, and output bytes by artifact class. No second full replay is authorized.

No acquisition, network request, redownload, source/test/CLI patch, cleanup, other product, final
bundle, catalog transaction, NautilusTrader check, experiment, backtest, model, trading engine, or
next ticket is authorized. Gate 2 remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS` until
reviewer acceptance of terminal evidence.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/437_CEX002_NATIVE_TIMESTAMP_CORRECTION_ACCEPTANCE_AND_RESUME.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted developer source/test drop, hidden data, runner evidence, the untracked wrapper, and
all unrelated dirty paths remain unstaged and untouched for Hermes.
