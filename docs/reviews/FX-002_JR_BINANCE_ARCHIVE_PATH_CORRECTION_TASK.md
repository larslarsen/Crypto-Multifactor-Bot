# FX-002 - JR BINANCE ARCHIVE PATH CORRECTION TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - ARCHIVE PATHS CORRECTED AND RECORDS PUBLISHED
**Next ticket:** `NONE`

## Assignment

Replace the malformed Binance archive evidence, correct its conclusions, and finish the two
mechanical gates. Do not repeat the broader provider audit and do not add implementation artifacts.

## Exact Archive Namespace

Use the required `/data/` component. Capture these bounded requests for both response bodies and
relevant response headers:

1. `https://data.binance.vision/data/spot/daily/klines/USDTUSD/1d/USDTUSD-1d-2022-05-01.zip`
2. `https://data.binance.vision/data/spot/daily/klines/USDCUSD/1d/USDCUSD-1d-2022-05-01.zip`
3. `https://data.binance.vision/data/spot/daily/klines/USDTUSD/1d/USDTUSD-1d-2026-07-20.zip`
4. `https://data.binance.vision/data/spot/daily/klines/USDCUSD/1d/USDCUSD-1d-2026-07-20.zip`
5. The `.CHECKSUM` sidecar for each successful 2026-07-20 ZIP.

Record exact retrieval UTC, HTTP status, body SHA-256, byte size, external path, `Last-Modified` or
explicit header absence, provider checksum, and local-versus-provider checksum result. Keep all raw
ZIPs, error bodies, checksums, and headers outside Git under `/tmp/fx_002_raw`.

## Required Conclusions

- A corrected 2022 404 may prove absence of that depeg-date object. Do not generalize it to "no
  archive" when a corrected recent object succeeds.
- If the recent objects succeed, classify historical coverage as recent/partial and depeg coverage as
  failed. Inspect the one-row daily CSV schema and confirm USD-per-stablecoin direction.
- Retain `UNKNOWN` fiat semantics, availability behavior, licensing, or revisions when still
  unsupported. Any one of those unknowns plus failed depeg coverage prevents PRIMARY.
- Recommend `NONE` only from the corrected evidence.

## Record Repairs

- Delete all malformed no-`/data/` evidence rows and claims.
- Replace every bare `N/A` with `NOT_APPLICABLE: <reason>` or `UNKNOWN: <reason>` in the register and
  source notes.
- Keep the required matrix schema from REVIEW-0085 and make report, matrix, register, and source note
  agree.

## Exact Mechanical Preflight

Run exactly, without replacement:

`rg -n '07:xx|\(from sprint|\(capture|\(size\)|~0|^CSV$|^cat research|actual output from run|tests passed with|standard warning' research/fx_002 docs/reviews/FX-002_SOURCE_FEASIBILITY_REPORT.md`

Record no output and exit status 1.

## Exact Acceptance Commands

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

The pytest run is incomplete for review purposes unless the report includes its literal final summary
line with pass count, warning count, and duration. Do not submit progress dots as a substitute.

## Records And Stop Condition

- Mark the Binance direct-USD audit task `FAILED - REVIEW-0086` and this task `COMPLETED` only after
  every requirement passes.
- Reconcile FX-002 as `AWAITING_REVIEW` in ticket, README, backlog, report, and handoff.
- Name Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, push, and stop.
