# FX-002 - JR BINANCE DIRECT-USD AUDIT TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - BOUNDED DIRECT-USD AUDIT AND RECORDS PUBLISHED
**Next ticket:** `NONE`

## Assignment

Audit the newly observed Binance `USDTUSD` and `USDCUSD` direct spot instruments as potential
historical USD-per-stablecoin sources. Repair the remaining REVIEW-0085 record failures. Do not add
production source, tests, schemas, migrations, datasets, ADRs, or architecture changes.

## Direct-Instrument Evidence

- Capture bounded symbol-specific official responses for `USDTUSD` and `USDCUSD`, including base
  asset, quote asset, status, retrieval UTC, HTTP status, SHA-256, byte size, and external path.
- Record direction as `USD per USDT` and `USD per USDC` when base/quote fields prove it.
- Locate exact official Binance documentation or an announcement that identifies what the `USD`
  quote asset represents. If this cannot be established, mark fiat-anchor semantics `UNKNOWN` and
  fail the direct-anchor gate.

## Historical And PIT Evidence

- Test official Binance public archive objects for both symbols and a daily interval. Record exact
  URLs, statuses, response/header hashes, byte sizes, `Last-Modified`/equivalent headers, and
  retrieval UTC.
- Test an object/window spanning the May 2022 stablecoin depeg period. A 404, absent listing, or
  later launch fails the required depeg-history gate; record the exact evidence.
- Determine the earliest observed archive coverage without guessing. Record the first available
  object/bar and how it was found.
- If archive data exists, inspect its provider timestamp fields and rate direction. Distinguish
  observation, close, publication, retrieval, and earliest defensible availability times.
- Capture provider checksums and any documented replacement/revision policy. Unknown revision or
  historical publication behavior fails the primary gate.
- Capture exact archive/API terms or licensing documentation. A generic homepage is not evidence;
  unknown licensing fails the primary gate.

## Remaining Provider Repairs

- Kraken: compute the actual SHA-256 of the retained external response once and make register,
  report, and source note identical. Remove unsupported alternative hashes.
- Coin Metrics: query the actual official asset-metric catalog for USDT/USDC. Do not treat
  `/catalog/assets` as a metric catalog. Record the exact result or exact blocked response.
- DefiLlama: retain only observed current-snapshot facts and complete exact metadata.
- Use the REVIEW-0084 register schema and reasoned `NOT_APPLICABLE: ...` or `UNKNOWN: ...` sentinels.

## Decision Rule

Recommend Binance as primary only if direct fiat-USD semantics, 2022 depeg history, observation and
availability times, revisions/checksums, raw reproducibility, and licensing all pass. Otherwise
recommend `NONE` with the first decisive failed gate and supporting evidence.

## Required Matrix

Use exactly:

`provider,direct_usd_anchor,rate_direction,historical_depth_observed,pit_times_distinguished,revisions_observed,depeg_sample,raw_reproducible,licensing_clear,source_status,recommendation`

## Mechanical Preflight

Run the exact REVIEW-0084 preflight command without substitution. Record its no-output result and
exit status 1.

## Acceptance Commands

Run exactly after final record reconciliation:

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

Record the literal control output and literal pytest final summary line, including pass count,
warning count, and duration. Do not omit or paraphrase the summary.

## Records And Stop Condition

- Mark the final-evidence recovery task `FAILED - REVIEW-0085` and this task `COMPLETED` only when all
  requirements are actually met.
- Reconcile FX-002 as `AWAITING_REVIEW` in ticket, README, backlog, report, and handoff.
- Name Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, push, and stop.
