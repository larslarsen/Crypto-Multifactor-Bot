# CEX-002 Record 433 — Review-432 Resume Terminal

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Record:** 433
- **Runner:** `/tmp/cex002_oi_432_f07dUK`

## Accepted source/test integration

The Review-430 source/test correction remains integrated and pushed at commit
`a243932d266b9a0ba88266af705febe9eaf91359`. `HEAD == origin/main == 68e806fb64d679fdb348d947650ecbb85ede94d4`
at record publication. No source/test/CLI patch, cleanup, or retry is authorized.

## One absolute-path supervisor launch

Review 432 authorized exactly one fixed `/tmp` supervisor. One runner was created:

| Runner | Start UTC | Shell PID | Shell start ticks | Python PID | Python start ticks |
|---|---|---|---|---|---|
| `/tmp/cex002_oi_432_f07dUK` | 2026-09-01T20:14:21Z | 1059806 | 9949798 | 1059812 | 9949800 |

The supervisor used absolute repository root, absolute Python, CLI, input, and output
paths, recorded both identity pairs, and returned immediately after confirming launch
metadata. No wrapper was created in the repository.

## Terminal exit 1 — receipt-directory mismatch

The runner recorded `exit_code = 1` at `2026-09-01T20:15:03Z` (42 seconds after start).
Python executed: `python_start_ticks = 9949800` is non-empty and `stderr.log` contains
a full normalizer traceback. stdout.log is empty.

The normalizer reached `load_generation0_sources` → `_require_fixed_generation0_terminal`
→ `authenticate_prefix` → `_validate_receipt_document` → `_authenticate_run_publication`,
which raised:

```
cryptofactors.acquisition.binance_usdm_harmonic_acquisition.UnsafeStateError: a receipt intent names a different run receipt directory
```

at `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py:6682`.

This is not a launch defect: Python ran and the normalizer reached the generation-0
receipt-authority stage. It is not a source-code or data-acquisition defect in the
open-interest normalizer itself. The receipt intent embedded in the retained
generation-0 state names a run receipt directory that does not match the expected run
directory, so the authority authenticator failed closed. No retry, source edit, test
rerun, cleanup, or reproduction is authorized.

## Live observation and termination

The launch harness returned live runner identities at launch. stderr.log proves the
normalizer was executing at approximately 31 seconds after start (reached receipt
authentication after loading generation-0 sources). The process then terminated at 42
seconds (20:15:03Z) with exit 1. No signal or interruption was sent to the runner.

## Hidden output unchanged

`data/.cex002_open_interest_5m` remains exactly as Review 432 preserved it:

- Eight content-addressed 0GUSDT Parquet partitions (2025-09 through 2026-04)
- Eight matching lineage JSONs
- Empty `.staging`
- No completion descriptor

No new partition, lineage, descriptor, or product was written. No mutation occurred.
No retry or data command was run.

## Control-plane disposition

The next required actor returns to the Lead Quantitative Finance Researcher/Engineer.
Next ticket remains `NONE`. Gate 2 remains accepted; CEX-002 and Gate 3 remain
`IN_PROGRESS`.
