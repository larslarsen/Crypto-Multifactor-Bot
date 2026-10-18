# CEX-002 Record 503 — Physical bound bundle preparation (terminal failure)

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 501 `research/sprint_004/501_CEX002_PHYSICAL_INVENTORY_BOUND_CORRECTION.md`, ADR-0037

## Outcome

The single authorized real preparation against the integrated physical-bound source FAILED
at `binance_usdm_liquidation_observed_daily` with blocker `row_mismatch` ("quality-gap rows
are not the accepted pin"). No candidate was created, no catalog row was admitted, no proof
or publication occurred, and the release remains non-consumable. No repair, retry,
private-function diagnostic, product-data inspection or data mutation was performed.

## Source identity

- Source integration commit bound to the producer: `05acac2f513074ceb413450b9bb1d241492d6dfb`
  (`CEX-002: derive physical inventory cap from accepted closure`).
- HEAD == origin/main at the start of this workflow: `05acac2f513074ceb413450b9bb1d241492d6dfb`.
- Index empty (0 staged) before the run.
- All five committed blobs at that commit were verified against the frozen hashes.

Five integrated source/test hashes:

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1370c63017275692c4b43c8577bcee8c3475ea357bf041a446a6ccec4debd3e5 | 1925 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | e91ac496b1de969b975c0dd95b3ef0c79340d7b0ed8f0ce6310761e917baf1b4 | 1239 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 |

Before the run the bundle root `data/.cex002_harmonic_bundle` was absent (`test -e` exit 1)
and not a dangling symlink (`test -L` exit 1). It remained absent after the failure.

## Producer execution

```
PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 05acac2f513074ceb413450b9bb1d241492d6dfb
```

Launched once via terminal background=true with notify_on_complete=true.
Native process: session `proc_df540b91aa3a`, PID 1418929, uptime 345s.
Terminal status: exited. Exit code: 1. Output (complete, 1 line):

```
row_mismatch: quality-gap rows are not the accepted pin | context={'blocker': 'row_mismatch', 'product': 'binance_usdm_liquidation_observed_daily'}
```

No duplicate run, unsupported foreground timeout, private-function diagnostic or retry was
attempted.

## Resource observations

- Free space before launch: 110,718,660,608 bytes.
- Free space after the failure: 110,578,511,872 bytes.
- Fixed allocations unchanged and not modified: 24,352,003 bundle-file cap,
  4,985,471,619 metadata remainder, 29,690,701,415 operating reserve.

## Catalog snapshot (read-only mode=ro, full ordered-row digests)

PRE-LAUNCH baseline (full digests captured BEFORE launch):

- `SELECT dataset_id, publication_uri FROM dataset WHERE transform_name = 'cex002_reference_publication' ORDER BY dataset_id;`
  -> 0 rows, ordered-row SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- `SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id;`
  -> 5 rows, ordered-row SHA-256 `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`.
  IDs/statuses: `ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea`, `ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933`, `ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512`, `ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8`, `ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb` — all REJECTED / REGISTERED.

POST-FAILURE: the same two queries returned identical ordered-row digests
(`4f53cda1…` and `b4334b2c…`) and the same five IDs/statuses. No catalog row was admitted by
the failed run.

## Scope limits and gaps

- No candidate metadata, descriptor, eleven manifests, inventory, footer or bundle Parquet
  exists; there is no candidate SHA to report.
- No proof/publication file, catalog admission, consumer run, external checker or preparation
  replay was performed.
- No private-function diagnostic, source/test edits, installs, acquisition, helpers or archive
  reads.
- No data writes occurred beyond the producer's own policy attempt; the bundle directory
  remains absent.
- The two earlier blockers (`reference_mismatch` on bar in Record 497; `metadata_bound` on
  flow in Record 500) were not re-observed here; this run failed later, at
  `binance_usdm_liquidation_observed_daily`.

## Record status

Record 503 documents a terminal producer failure. It claims no release or Gate acceptance.
CEX-002 remains IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
