# FX-002 - JR FINAL EVIDENCE RECOVERY TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes, fresh reliable execution required
**Status:** COMPLETED - EVIDENCE RECOVERED AND RECORDS PUBLISHED
**Next ticket:** `NONE`

## Routing Constraint

Do not use the execution configuration responsible for the prior three failed submissions. Use a Jr
model/configuration with demonstrated reliable file editing, network capture, command execution, and
literal output reporting.

## Assignment

Recover exact evidence first, then rewrite the records from that evidence. This is not a prose-editing
exercise. Do not add production source, tests, schemas, migrations, datasets, ADRs, or architecture
changes.

## Evidence Register Schema

Replace the register with valid CSV using exactly these columns:

`evidence_id,provider,request_url,retrieval_utc,http_status,sha256,byte_size,external_path,returned_bounds,rate_direction,licensing_url,licensing_status,notes`

Rules:

- One header and one row per retained capture; no command text or heredoc markers.
- Full URLs only. UTC must be a complete ISO-8601 timestamp.
- SHA-256 must be 64 lowercase hexadecimal characters for every response body, including errors.
- Byte size must be an integer. HTTP/provider status must be observed, not inferred.
- Use `NOT_APPLICABLE: <reason>` or `UNKNOWN: <reason>` only when a field truly cannot apply or was
  not established.
- `/tmp/fx_002_raw` remains approved external staging. Commit no provider payloads.
- A licensing URL must identify actual terms/documentation, with its observed retrieval status.
  Otherwise use `UNKNOWN: no terms evidence` and fail the gate.

## Required Captures

### Kraken

- Retain or re-capture only the old-`since` request that proves the recent-window cap. Remove the
  redundant recent row unless every field can be verified exactly.
- Record exact returned row count and minimum/maximum epochs with ISO-8601 conversions.
- Describe the response timestamp only as the OHLC interval timestamp unless official documentation
  proves a narrower meaning. It is not publication or availability time.

### Coin Metrics

- Make an actual unauthenticated Community catalog request for USDT and USDC asset metrics using the
  official API behavior and documentation. Record its exact response.
- Identify the exact USD price/reference-rate metric and Community coverage if present. Do not query
  invented `price_usd` unless the catalog returns that exact identifier.
- If a candidate metric is present, make one bounded 2022 date-window timeseries request without
  `limit`; otherwise reject from the exact catalog result.

### DefiLlama

- Re-capture the exact repository-known endpoint
  `https://stablecoins.llama.fi/stablecoins?includePrices=true` with complete metadata.
- Record the observed schema fact that proves whether the response is current-only or historical.
  Do not infer historical availability from current price fields.

### Binance

- Capture `https://api.binance.com/api/v3/exchangeInfo` without a single-symbol filter and inspect the
  returned instrument list for actual fiat `USD` base/quote assets.
- Do not use `USDC`, `USDT`, another stablecoin, or an invalid cross symbol as proof about fiat USD.
- If access is blocked, record the exact HTTP status/body hash and mark the direct-USD gate `UNKNOWN`;
  unknown still cannot qualify as primary.

## Analytical Records

- Rewrite every source note from the registered captures. Remove unverified claims.
- Rewrite the decision matrix with these columns:
  `provider,direct_usd_anchor,rate_direction,historical_depth_observed,pit_times_distinguished,revisions_observed,depeg_sample,raw_reproducible,licensing_clear,source_status,recommendation`.
- Make report, notes, register, and matrix agree. `NONE` is required unless one candidate passes every
  original mandatory gate.
- Remove all claims that evidence is "exact" unless every field above is populated from observation.

## Mechanical Preflight

Run this exact command after editing:

`rg -n '07:xx|\(from sprint|\(capture|\(size\)|~0|^CSV$|^cat research|actual output from run|tests passed with|standard warning' research/fx_002 docs/reviews/FX-002_SOURCE_FEASIBILITY_REPORT.md`

Expected result: no output and exit status 1. If it finds anything, fix it before submission.

## Acceptance Commands

Run exactly after setting all repository records to their final review state:

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

Record the literal output `Repo control check: PASS` and the literal pytest final summary line with
pass count, warning count, and duration. Do not paraphrase, predict, or reuse a prior run.

## Records And Stop Condition

- Mark REVIEW-0084's predecessor task `FAILED - REVIEW-0084` and this task `COMPLETED` only after all
  requirements pass.
- Reconcile FX-001 as `ACCEPTED` and FX-002 as `AWAITING_REVIEW` in ticket, README, backlog, report,
  and handoff.
- Name Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, push, and stop.
