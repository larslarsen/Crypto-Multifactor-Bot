# CEX-002 Record 497 — First real bundle preparation (terminal failure)

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 496 `research/sprint_004/496_CEX002_REAL_BUNDLE_PREPARATION_REVIEW.md`, ADR-0037

## Outcome

The single authorized real preparation FAILED at `binance_usdm_bar_1h`, the SECOND product
in `PRODUCTS` order. The producer exited 1 with blocker `reference_mismatch` for that
product. No candidate was created, no catalog row was admitted, no proof or publication
occurred, and the release remains non-consumable. No repair, retry or data mutation was
performed.

## Source identity

- Accepted source commit bound to the producer: `30719fdd2a0e71ed8266d8ce50564f4dc5efaea5`
- HEAD == origin/main at the start of this workflow: `f72ded0f7ac5181267ad62a496f062520ce3bb05`
  (reviewer governance had advanced HEAD past the source commit; all five accepted blobs
  exist at 30719fd, per Review 496).
- Index empty (0 staged) before the run.

Five integrated source/test hashes (Record 495 bytes, re-verified before the run):

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | dedf31e1996a71c055560b40558a6f1e2a86f8429da805d4cf17a02caf87355e | 1848 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | d245e6195f5619a3d2c5594bb3a1edf4a5345b2696486a352b5af398b3681553 | 101 |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | d33da132d17026b3042aa26f8142f6ba6fe8758c2377705b96141d46a1102d1a | 1088 |

No existing bundle artifact was present before the run: `data/.cex002_harmonic_bundle`
did not exist (`test -e` exit 1). No bundle directory was created by the failed run.

## Producer execution (step 3)

```
PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 30719fdd2a0e71ed8266d8ce50564f4dc5efaea5
```

Launched once via terminal background=true with notify_on_complete=true.
Native process: session `proc_11b8c71b71af`, PID 1263330, uptime 269s.
Terminal status: exited. Exit code: 1. Output (complete, 1 line):

```
reference_mismatch
```

The CLI's `except DatasetError` handler writes only `str(exc.context.get("blocker"))` to
stderr, so the message text and context were not shown by the producer. No duplicate run,
foreground timeout or retry was attempted.

## Read-only diagnostic (reviewer-authorized, post-failure)

One inline read-only invocation using existing module functions only; no writer functions,
no producer retry, no helper file.

```
PYTHONPATH=src .venv/bin/python <<'PY'
from pathlib import Path
from cryptofactors.ingest.binance_usdm_harmonic_bundle import (
    PRODUCTS,
    _account_product,
    _authenticate_authorities,
    _authenticate_reconciliation,
)
from cryptofactors.catalog.dataset.errors import DatasetError

root = Path('/home/lars/Crypto_Multifactor_Bot')
sizing, authorities = _authenticate_authorities(root, True)
print('AUTHORITIES_OK')
accounts = {}
try:
    for spec in PRODUCTS:
        print('PRODUCT', spec.dataset_type)
        accounts[spec.dataset_type] = _account_product(root, spec, sizing, True)
except DatasetError as exc:
    print('DATASETERROR_STR', str(exc))
    print('DATASETERROR_CONTEXT', dict(getattr(exc, 'context', {}) or {}))
    print('DATASETERROR_BLOCKER', getattr(exc, 'blocker', None))
    raise SystemExit(0)
qual = authorities['authenticated_files']['qualification_report_sha256']
recon = _authenticate_reconciliation(root, accounts, qual, True)
print('RECON_OK', dict(recon))
PY
```

Output (accurate concise summary; not a verbatim transcript):

```
AUTHORITIES_OK
PRODUCT binance_usdm_perpetual_membership
PRODUCT binance_usdm_bar_1h
DATASETERROR_STR product tree does not match the reconstructed artifacts | context={'blocker': 'reference_mismatch', 'product': 'binance_usdm_bar_1h', 'extra': [<8 .lineage/0GUSDT/YYYY-MM/*.json paths, listed below>], 'missing': []}
DATASETERROR_CONTEXT {'blocker': 'reference_mismatch', 'product': 'binance_usdm_bar_1h', 'extra': [<same 8 .lineage paths>], 'missing': []}
DATASETERROR_BLOCKER reference_mismatch
```

The `extra` list (8 `.lineage/0GUSDT/YYYY-MM/*.json` paths) was:

```
.lineage/0GUSDT/2025-09/af2c6111f3c32930097077a00af38dba57e5140dceae32d4ddcc50d83df76210.json
.lineage/0GUSDT/2025-10/0f478d26e9aca6796c740ad5d8945f4677fd2a9fc7840b00113d17a174439d04.json
.lineage/0GUSDT/2025-11/0cb39b9a2bd72149ff24ccd444860462824100ab6828c442405fc189aaa83842.json
.lineage/0GUSDT/2025-12/fbe6d1d00a5437a88af832207152e5ea7355c5bb9b142946bfb2726df3463a6d.json
.lineage/0GUSDT/2026-01/77006313d31b4b52066b64c2c0c9259ae47bf7458c72e94c5a0b1dd918f7907f.json
.lineage/0GUSDT/2026-02/55e7eaa3c02c638339ae606a20acb179ffb82de936311d1e78defaf225c1d74d.json
.lineage/0GUSDT/2026-03/80be109c819f645a075e38beb46c2ed02bfff71e2520c07cb028ed70e985592b.json
.lineage/0GUSDT/2026-04/3cfa5f83c788a3b2f79a8e7f898dab5e799f91cc745ff5d36a307191165a64be.json
```

Exit status: the diagnostic exited 0 (the DatasetError was caught and the script ended via
`raise SystemExit(0)`); the producer exited 1.

Diagnostic finding (Hermes's observation, not a reviewer conclusion): the blocker is the
`reference_mismatch` gate in `_account_product` (module line 1385-1392), which compares
the declared file set reconstructed from the sealed artifacts against the on-disk tree
(`_walk`). For `binance_usdm_bar_1h` the on-disk `data/.cex002_bar_1h/.lineage/0GUSDT/...`
tree contains `.lineage` JSON files that the reconstruction does not declare, so
`declared != disk`. `missing` is empty; only `extra` entries exist. `binance_usdm_bar_1h` is the SECOND product
in `PRODUCTS` order; the FIRST product, `binance_usdm_perpetual_membership`, passed before
this failure. `_authenticate_reconciliation` was not reached (its precondition is successful
accounting of all products).

Reviewer explanation (attributed, not independently verified by Hermes): Review 460 excludes
retained older artifacts from accepted descriptors, and Record 459 gives the older counts
(bar 31 Parquets + 20,335 lineages; flow 47 + 20,335). Review 498 assigns a source
correction to the existing GPT-6 Sol actor in the ingest module, CLI and ingest tests. The
failure is recorded against the failed source commit 30719fd bytes above, not against the
new unintegrated drop.

## Resource observations

- Free space before the run: 118,263,750,656 bytes.
- Free space after the failure: 117,461,798,912 bytes.
- Fixed allocations unchanged and not modified: 24,352,003 bundle-file cap,
  4,985,471,619 metadata remainder, 29,690,701,415 operating reserve.

## Catalog snapshot

Read-only SQLite snapshot via URI `mode=ro`, two ordered queries.

PRE-RUN: the query returned 0 rows for `cex002_reference_publication` and 5 rows for the
`cex002_bitmex_false_authority` marker. The pre-run capture recorded only the dataset IDs
and their status pairs plus 80-character `quality_summary_json` prefixes. No full pre-run
digest was captured (the full ordered-row digests below were taken after launch); no full
pre-run baseline digest is claimed or fabricated.

POST-LAUNCH AND POST-FAILURE/DIAGNOSTIC: full ordered-row digests are identical between
these two captures:

- `SELECT dataset_id, publication_uri FROM dataset WHERE transform_name = 'cex002_reference_publication' ORDER BY dataset_id;`
  -> 0 rows, SHA-256 of ordered rows `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- `SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id;`
  -> 5 rows, SHA-256 of ordered rows `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`.
  IDs/statuses: `ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea`, `ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933`, `ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512`, `ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8`, `ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb` — all REJECTED / REGISTERED.

No complete before/after byte-equality claim is made: the before snapshot has truncated
summary prefixes only, while the after snapshots carry full digests. The full digests were
captured post-launch and again post-failure/diagnostic; the post-failure digest equals the
post-launch digest, so no catalog row was admitted by the failed run.

## Scope limits and gaps

- No candidate metadata, descriptor, inventory or footer exists; there is no candidate SHA
  to report.
- No real prepare replay, catalog admission, proof generation, consumer run or external
  checker was performed.
- No source/test edits, installs, acquisition, helpers or archive reads.
- No data writes occurred beyond the producer's own policy attempt; the bundle directory
  remains absent.
- Reviewer governance edits in CURRENT_TASK/Review496/ticket are outside this record's
  staging scope and were preserved.

## Record status

Record 497 documents a terminal producer failure and the authorized read-only diagnostic.
It claims no release or Gate acceptance. CEX-002 remains IN_PROGRESS; next ticket NONE;
reviewer acceptance remains exclusive.
