# CEX-002 Review 507 — Compact the CEX schema metadata without weakening reserves

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Architecture: ADR-0038, extending ADR-0037
Disposition: bounded two-path source correction; no real retry or cleanup

## Diagnosed result and next decision

Review 504 accepts integration 42ecac90f5c47411d4d098cf68e046257bab3a97 and its
149-case/lint/control results. The one real prepare passed all ten product accounts,
wrote the new bundle object, then exited 1 at the prepare-stage metadata guard:
7,450,831,574 calculated bytes exceeds 4,985,471,619. Preserve that guard and every
existing allocation. No completed prepared descriptor/candidate SHA was emitted.
Hermes is completing terminal Record 506 only, without source staging or cleanup.

The source repeats a full field contract in every table partition, stores the same
partition JSON in SQLite, and conservatively reserves twelve times serialized record
bytes. ADR-0038 authorizes a per-manifest schema registry with authenticated references,
preserving the reservation formula rather than reducing its multiplier. The detailed
real manifest/SQLite subtotal is unknown and must not be invented.

The reviewer then counted filenames only across the ten accepted product roots,
subtracting the already frozen 31/20,335 and 47/20,335 retained kline inventories.
No table bytes were read by that inventory. Accepted counts are:

| Product | Files | Parquet tables |
|---|---:|---:|
| membership | 1,543 | 771 |
| bar | 45,269 | 22,634 |
| flow | 45,269 | 22,634 |
| open interest | 39,491 | 19,745 |
| realized funding | 42,071 | 21,035 |
| indicative funding | 45,245 | 22,622 |
| basis | 51,345 | 25,672 |
| liquidation | 37,890 | 18,944 |
| cost | 7,732 | 3,865 |
| coverage | 107,590 | 21,024 |
| Ten-product total | 423,445 | 178,946 |

With the new bundle table, the eleven manifests need 423,446 file references:
178,947 tables and 244,499 metadata files. This complete count supersedes the
earlier 147,081-reference stress scale for this new regression. Use realistic distinct
table contracts, metadata rows, long paths and proof/publication headroom at this scale.

The reviewer observed one producer-owned object before failure:
data/.cex002_harmonic_bundle/.objects/89/8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f,
13,232,150 bytes. It is not a completed release. Preserve it during this assignment;
the next real-run prompt must address this exact leftover explicitly before spending
another object's bytes. No accepted product may be deleted, moved, rewritten or copied.

## One-way source prompt

Continue the owner-approved direct source route using the existing GPT-6 Sol High
actor. It authored the accepted catalog adapter and its corrective integrations; this
bounded catalog representation change benefits from that context. GPT-6.1 stays reviewer.
Read CURRENT_TASK, this review and ADR-0038. Exactly two writable paths:

1. src/cryptofactors/catalog/dataset/cex002_reference_release.py
2. tests/catalog/test_cex002_reference_release.py

Implement the ADR's strict shared schema registry. Bound registry count/bytes explicitly;
use canonical ordered-field hashes and identity-bearing quality metadata. Table entries
carry references; metadata entries stay zero-row metadata. Advance only the CEX reference
transform protocol version, with no generic model, SQL schema or product-format changes.
Resolve and authenticate contracts at every sealed-manifest/footer use, including publish,
read and replay. Refuse unknown/missing/changed/malformed/mixed contracts and inconsistent
registry versions; preserve all existing schema, file, proof and transaction checks.
Do not accept a schema reference by looking only at the actual footer or by trusting its
hash without the manifest-bound field contract.

Keep the current SQLite reservation formula/multipliers and all resource pins unchanged.
Count registry and file-reference bytes in the existing real charges. Add exact manifest,
descriptor/proof/leftover and SQLite charged subtotals to resource failures where available;
do not alter first-failure behavior or fabricate subtotals.

Add meaningful tests for shared contracts, identity changes on contract/reference tamper,
publication/read/replay refusal, metadata exclusion, decimal/dictionary/list preservation
and unchanged logical proof tokens. Strengthen the existing large-inventory resource
regression with realistic table AND metadata counts and long paths/representative contracts;
account for all eleven manifests, SQL reserve, proof/publication headroom and the fixed
4,985,471,619 remainder. The test must not merely lower the reservation or mock its result.
Use bounded synthetic manifest metadata; no hundreds-of-thousands-file creation or real
product/accounting/proof run. Return the synthetic charged breakdown and explain its count
basis, so the reviewer can assess the real-run fit before authorizing another long attempt.

All three ingest/CLI/test paths from Review 504 are read-only. No repository records,
Git, integration, helpers, installation, network, real-data reads/writes, cleanup or subagents.
After editing, run exactly once under the targeted senior exception:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

Stop on first nonzero without edits/retry. Return full output/exit, two hashes/line counts,
the synthetic resource evidence and concise source notes, then stop for reviewer inspection.
No real prepare, catalog mutation, consumer run or next ticket is authorized.

Reviewer publication scope is exactly this Review 507, ADR-0038,
research/sprint_004/504_CEX002_LIQUIDATION_GAP_ACCOUNTING_CORRECTION.md,
docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. No source/test integration or
implementation evidence is included.
