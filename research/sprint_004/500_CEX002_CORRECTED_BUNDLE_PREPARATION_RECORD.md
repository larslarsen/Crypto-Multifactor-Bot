# CEX-002 Record 500 — Corrected bundle preparation (terminal failure)

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 498 `research/sprint_004/498_CEX002_RETAINED_KLINE_INVENTORY_CORRECTION.md`, ADR-0037

## Outcome

The single authorized real preparation against the integrated corrected source FAILED at
`binance_usdm_trade_flow_1h` with blocker `metadata_bound` ("kline physical inventory
exceeds the accepted bound"). No candidate was created, no catalog row was admitted, no
proof or publication occurred, and the release remains non-consumable. No repair, retry,
private-function diagnostic, product-data inspection or data mutation was performed.

## Source identity

- Source integration commit bound to the producer: `2395f03850c3941ed0e1145053f743b6c5f69c4c`
  (`CEX-002: preserve excluded kline inventory during bundle preparation`).
- HEAD == origin/main at the start of this workflow: `2395f03850c3941ed0e1145053f743b6c5f69c4c`.
- Index empty (0 staged) before the run.
- All five committed blobs at that commit were verified against the frozen hashes.

Five integrated source/test hashes:

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 6018280a0ed9ab16b585875e7f1c3bd3bc96233c90407b1b5bcb7f2a222c276a | 1921 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 08fc013675d70d31c3ef578d7c2ce810979485ecded032a916f0a29832ee02b9 | 1203 |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 |

Before the run the bundle root `data/.cex002_harmonic_bundle` was absent (`test -e` exit 1)
and not a dangling symlink (`test -L` exit 1). It remained absent after the failure.

## Producer execution

```
PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 2395f03850c3941ed0e1145053f743b6c5f69c4c
```

Launched once via terminal background=true with notify_on_complete=true.
Native process: session `proc_caa44bb65052`, PID 1286281, uptime 80s.
Terminal status: exited. Exit code: 1. Output (complete, 1 line):

```
metadata_bound: kline physical inventory exceeds the accepted bound | context={'blocker': 'metadata_bound', 'product': 'binance_usdm_trade_flow_1h'}
```

The CLI now exposes the original message/context for this failure (unlike the earlier
`reference_mismatch` output, which showed only the blocker). No duplicate run, unsupported
foreground timeout or retry was attempted.

## Resource observations

- Free space before launch: 116,312,014,848 bytes.
- Free space after the failure: 116,272,734,208 bytes.
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
- The `binance_usdm_bar_1h` blocker from the earlier failed source (Record 497) was not
  re-observed here; this run failed later, at `binance_usdm_trade_flow_1h`.

## Record status

Record 500 documents a terminal producer failure. It claims no release or Gate acceptance.
CEX-002 remains IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
