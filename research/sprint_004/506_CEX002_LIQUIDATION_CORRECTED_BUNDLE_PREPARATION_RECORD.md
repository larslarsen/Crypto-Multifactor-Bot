# CEX-002 Record 506 — Liquidation corrected bundle preparation (terminal failure)

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 504 `research/sprint_004/504_CEX002_LIQUIDATION_GAP_ACCOUNTING_CORRECTION.md`, ADR-0037

## Outcome

The single authorized real preparation against the integrated liquidation-category source
FAILED at the final prepare metadata guard with blocker `metadata_remainder_exceeded`
("new release metadata exceeds the post-coverage remainder"). No completed prepared
descriptor, candidate identity or consumable release was emitted. No catalog row was
admitted, no proof or publication occurred, and the release remains non-consumable. No
repair, retry, private-function diagnostic, product-data inspection or data mutation was
performed.

This run progressed past all three earlier blockers (bar `reference_mismatch` in Record
497, flow `metadata_bound` in Record 500, liquidation `row_mismatch` in Record 503) and
stopped at the final metadata-remainder guard, a new and later capacity blocker.

## Source identity

- Source integration commit bound to the producer: `42ecac90f5c47411d4d098cf68e046257bab3a97`
  (`CEX-002: preserve liquidation gap categories and comparison provenance`).
- HEAD == origin/main at the start of this workflow: `42ecac90f5c47411d4d098cf68e046257bab3a97`.
- Index empty (0 staged) before the run.
- All five committed blobs at that commit were verified against the frozen hashes.

Five integrated source/test hashes:

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b | 1996 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0 | 1383 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 |

## Producer execution

```
PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 42ecac90f5c47411d4d098cf68e046257bab3a97
```

Launched once via terminal background=true with notify_on_complete=true.
Native process: session `proc_311fa1978b3f`, PID 1612662, uptime 1084s.
Terminal status: exited. Exit code: 1. Output (complete, 1 line):

```
metadata_remainder_exceeded: new release metadata exceeds the post-coverage remainder | context={'blocker': 'metadata_remainder_exceeded', 'stage': 'prepare', 'metadata_bytes': 7450831574, 'metadata_remainder_bytes': 4985471619, 'release_metadata_bytes': 5556368003}
```

Exact context values: `metadata_bytes` 7,450,831,574; `metadata_remainder_bytes`
4,985,471,619; `release_metadata_bytes` 5,556,368,003. No duplicate run, unsupported
foreground timeout, private-function diagnostic or retry was attempted.

## Owned bundle root state (terminal failure path)

The owned bundle root `data/.cex002_harmonic_bundle` was absent before the run (`test -e`
exit 1, no dangling symlink). After the terminal failure it exists (`test -e` exit 0):
the producer created its owned directory and began writing before the final metadata guard
stopped it. No completed prepared descriptor or candidate identity was emitted.

Reviewer metadata observation (attributed to the reviewer, not independently verified by
Hermes): before the terminal failure the reviewer observed the new owned data object
`data/.cex002_harmonic_bundle/.objects/89/8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f`,
stat size 13,232,150 bytes. Hermes performed no additional product inspection or
diagnostic. Created files are preserved; no cleanup or retry.

## Resource observations

- Free space before launch: 78,953,398,272 bytes.
- Free space after the failure: 76,807,471,104 bytes.
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

- No completed prepared descriptor, eleven named manifests, bundle Parquet, candidate SHA or
  footer inspection exists; the producer stopped at the final metadata guard before emitting
  them.
- No proof/publication file, catalog admission, consumer run, external checker or preparation
  replay was performed.
- No private-function diagnostic, source/test edits, installs, acquisition, helpers or archive
  reads.
- Created owned files are preserved; no cleanup or retry.
- The exact `metadata_bytes` charge and `release_metadata_bytes` subtotal are the producer's
  emitted context values; Hermes did not independently recompute or attribute a SQLite/
  manifest subtotal that the command did not emit.

## Record status

Record 506 documents a terminal producer failure. It claims no release or Gate acceptance.
CEX-002 remains IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
