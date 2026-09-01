# CEX-002 Record 435 — Review-434 Resume Terminal

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Record:** 435
- **Runner:** `/tmp/cex002_oi_434_DmfuB0`

## Accepted source/test integration

The Review-430 source/test correction remains integrated and pushed at commit
`a243932d266b9a0ba88266af705febe9eaf91359`. `HEAD == origin/main ==
9db8583ed39a0a4bf96fe4eb56cbbf58830b265c` at record publication. No source/test/CLI
patch, cleanup, or retry is authorized.

## One absolute-path supervisor launch

Review 434 authorized exactly one fixed `/tmp` supervisor. One runner was created:

| Runner | Start UTC | Shell PID | Shell start ticks | Python PID | Python start ticks |
|---|---|---|---|---|---|
| `/tmp/cex002_oi_434_DmfuB0` | 2026-09-01T20:24:54Z | 1065195 | 10013000 | 1065202 | 10013002 |

The supervisor set `REPO_ROOT=/home/lars/Crypto_Multifactor_Bot`, `cd`'d to it,
used absolute Python and CLI paths, preserved every accepted repository-relative
authority and output argument exactly, recorded both identity pairs, and returned
immediately after confirming launch metadata. No wrapper was created in the
repository.

## Successful path-identity passage

The supervisor used the exact repository-relative authority identities from Review
434. The normalizer passed the generation-0 receipt-authentication stage that failed
in Review 432 (`_authenticate_run_publication` → receipt-directory equality), loaded
generation-0 sources, descended the open-interest tree into per-row timestamp
validation, and reached `_timestamp` at `src/cryptofactors/ingest/binance_usdm_open_interest.py:801`.
The path-identity resume is successful: the accepted relative arguments authenticate
and run deep into the normalizer.

## Terminal exit 1 — metrics create_time off the five-minute grid

The runner recorded `exit_code = 1` at `2026-09-01T20:31:10Z` (6 minutes 16 seconds
after start). Python executed: `python_start_ticks = 10013002` is non-empty and
`stderr.log` contains a full normalizer traceback. stdout.log is empty.

The normalizer reached `normalize_from_authorities` → `_normalize_open_interest_tree`
→ `_row_values` → `_timestamp`, which raised:

```
cryptofactors.ingest.binance_usdm_open_interest.OpenInterestNormalizationError: metrics create_time is off the five-minute grid
```

at `_require` via `value % (EXPECTED_CADENCE_SECONDS * 1000) == 0` at
`src/cryptofactors/ingest/binance_usdm_open_interest.py:801`, called from
`_row_values` line 830, `_normalize_open_interest_tree` line 1250,
`normalize_from_authorities` line 1486.

This is a bounded normalizer defect in per-row five-minute-grid validation, not a
launch, receipt-authentication, or authority-identity defect. The resume proved the
relative path identity works and the normalizer is now processing real rows. No
retry, source edit, test rerun, cleanup, or reproduction is authorized.

## Live observation and termination

The launch harness returned live runner identities at launch. stderr.log proves the
normalizer was executing through generation-0 authentication and deep into the
open-interest tree for over six minutes. The process terminated at 20:31:10Z with
exit 1. The lead reviewer interrupted only the still-waiting Hermes harness after
the runner was already terminal; no live runner was signaled. No retry or cleanup
occurred.

## Hidden output

`data/.cex002_open_interest_5m` now contains:

- 181 content-addressed Parquet partitions in `.partitions/`
- 181 matching lineage JSONs in `.lineage/`
- Empty `.staging/`
- No completion descriptor

The last published partition is `1000FLOKIUSDT/2024-03/baada928bdfb4fc3f505afcbe7a46957bb957919551379d974ef1cbbfb27c457.parquet`.

This is 173 new pairs beyond the prior eight 0GUSDT months (2025-09 through 2026-04).
No mutation of the prior eight occurred. No retry or data command was run.

## Control-plane disposition

The next required actor returns to the Lead Quantitative Finance Researcher/Engineer.
Next ticket remains `NONE`. Gate 2 remains accepted; CEX-002 and Gate 3 remain
`IN_PROGRESS`.
