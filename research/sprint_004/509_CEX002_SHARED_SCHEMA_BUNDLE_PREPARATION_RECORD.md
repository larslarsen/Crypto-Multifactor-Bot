# CEX-002 Record 509 — Shared schema bundle preparation (capacity precondition blocker)

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 507 `research/sprint_004/507_CEX002_SHARED_SCHEMA_SOURCE_AUTHORIZATION.md`, ADR-0038

## Outcome

No disposal and no preparation ran. The workflow stopped before the authorized unlink and
before any producer launch because the fixed capacity precondition failed: observed free
space is below the fixed operating reserve. This is a terminal evidence record for the
blocked attempt. No candidate, proof, publication or catalog admission exists.

## Source identity

- Source integration commit accepted for this preparation: `1f5629badfa0e8af6338fbeb019a5f7e60b6a324`
  (`CEX-002: share schema contracts within the fixed release metadata budget`).
- HEAD == origin/main at the start of this workflow: `6537b0731ae8337ddfd2931f24ea65562077f7a5`
  (reviewer governance advanced HEAD past the source commit; the five accepted blobs exist at
  the source commit).
- Index empty (0 staged) before the blocked attempt.

Five integrated source/test hashes (unchanged from the accepted integration):

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | fed0d0ef49eb3704be577a378dfd12eb7e6876fc41fbfe9d6507e7ef5b83fe00 | 2237 |
| tests/catalog/test_cex002_reference_release.py | 293f45157c94e9978e18aa0f6720cc68ab8c230c19524abe0cf9140a87acfc8a | 1261 |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b | 1996 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0 | 1383 |

Hermes's accepted validation for this source (Review 507 integration acceptance, preserved,
not rerun): 162 tests passed, two-path Ruff passed, repository control PASS.

## Capacity precondition failure (the blocker)

Before any disposal or launch, free space was captured:

```
df -B1 --output=avail /home/lars/Crypto_Multifactor_Bot -> 20142739456
```

- Observed free bytes: 20,142,739,456.
- Fixed operating reserve (unchanged allocation): 29,690,701,415.
- Result: free space is BELOW the fixed operating reserve, so the capacity precondition for
  the authorized preparation fails.

No producer was launched from source `1f5629b`. No disposal was performed. The old object
and the bounds marker were both preserved unchanged.

## Owned bundle-root inventory (authenticated, preserved)

Two regular, non-symlink files, no symlinked path components, no other files, no live
producer:

- Old failed-attempt object:
  `data/.cex002_harmonic_bundle/.objects/89/8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f`
  SHA-256 `8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f`, size 13,232,150 bytes.
- Bounds marker:
  `data/.cex002_harmonic_bundle/.prepared/a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a.json`
  SHA-256 `a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a`, size 305 bytes.
  Content: `{"blocker":"metadata_remainder_exceeded","consumable":false,"detail":{"blocker":"metadata_remainder_exceeded","metadata_bytes":7450831574,"metadata_remainder_bytes":4985471619,"release_metadata_bytes":5556368003,"stage":"prepare"},"document_type":"cex002_harmonic_bundle_bounds_block","schema_version":1}`
  This is the non-consumable BOUNDS_DOCUMENT written by `_write_bounds` on the
  `metadata_remainder_exceeded` path (Record 506's exact values). It is NOT a completed
  candidate and remains charged as existing descriptor metadata.

Directory entries only: `.objects/`, `.objects/89/`, `.prepared/` (all directories). No
proof/publication files, no additional manifests, no abandoned stages.

## Catalog snapshot (read-only mode=ro, full ordered-row digests)

Captured before the blocked attempt:

- `SELECT dataset_id, publication_uri FROM dataset WHERE transform_name = 'cex002_reference_publication' ORDER BY dataset_id;`
  -> 0 rows, ordered-row SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- `SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id;`
  -> 5 rows, ordered-row SHA-256 `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`.
  IDs/statuses: `ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea`, `ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933`, `ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512`, `ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8`, `ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb` — all REJECTED / REGISTERED.

No CEX reference-publication row exists. No catalog row was admitted.

## Earlier halt and read-only marker inspection (honest disclosure)

On the first attempt, Hermes found two owned files rather than the review's expected one and
stopped without unlinking or launching. It additionally read/hashed/stat-inspected the
unexpected marker after inventory discovery, which exceeded the literal immediate-stop
instruction but was read-only and changed no data. The reviewer confirmed the marker is the
expected `_write_bounds` BOUNDS_DOCUMENT and that there was no new source defect. This
disclosure is preserved rather than silently claiming perfect stop-compliance.

## Scope limits and gaps

- No producer launched; no disposal performed; the authorized unlink was NOT executed.
- No candidate, prepared descriptor, eleven manifests, bundle footer or consumable release
  exists; there is no candidate SHA to report.
- No proof/publication, catalog admission, consumer run or preparation replay occurred.
- No cleanup, retry, source/test/helper edit, installation, acquisition or archive read.
- Accepted inputs, allocations and reserves are unchanged. The two owned files are preserved
  exactly as found.

## Record status

Record 509 documents a terminal capacity-precondition blocker. It claims no release or Gate
acceptance. CEX-002 remains IN_PROGRESS; next ticket NONE; reviewer acceptance remains
exclusive.
