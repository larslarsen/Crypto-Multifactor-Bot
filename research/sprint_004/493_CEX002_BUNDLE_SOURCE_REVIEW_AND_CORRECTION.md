# CEX-002 Review 493 — Bundle source review and correction

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Disposition: source snapshot requires correction; no integration or real run accepted
Senior corrective actor: Grok Build, native grok-4.7 High

## Scope and review boundary

This is the consolidated review of Review 492's five-path drop. Keep the accepted ten
products, reconciliation and ADR-0037 design unchanged. GPT-6.1 Sol remains reviewer;
it has authored no production or test code and has executed no tests. The source
author remains Grok: this is its first correction of this drop, substantial Grok usage
is expiring, and the reviewer also supplied an incorrect sizing premise below.

Only these developer paths remain writable:

1. src/cryptofactors/catalog/dataset/cex002_reference_release.py
2. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
3. scripts/research/publish_binance_usdm_harmonic_bundle.py
4. tests/catalog/test_cex002_reference_release.py
5. tests/ingest/test_binance_usdm_harmonic_bundle.py

Reviewed source snapshot (SHA-256, in path order above):

```
149ed47fbe133556d3501998c8c805eb99c8a2ce930a3892df087473248c38f2  1439 lines
414740f0745b923391dde155d0164e78eeac80203635505ace2d0ab9efd28a3b  1542 lines
8eae74bd9751c96de2066aff63f27c671773d79bd4fb96b757d8f43f571d2a59    98 lines
155b479a9c299e579a9c1642d2a2f01edd5aaa5be29f786f992b2fd6cdd36766   636 lines
f358fd8c8ecb6ce9f1304ce67021741821afc116b457ca799b310fbfd06ff5cb   722 lines
```

The reviewer measured these hashes directly. All five files were saved and fully
reviewed; the reviewer interrupted subsequent Grok generation to freeze this snapshot
and deliver the consolidated correction, before a formal author hash return. No test
command ran during the original source assignment. No developer files are integrated.

This review does not add acquisition, normalizer, generic catalog, migration, dependency,
consumer-checker, economic-research or trading work. Address the blocking requirements
below together, then return the complete five-path correction for review.

## Reviewer correction: authenticate the actual sizing terms

Review 492 incorrectly identifies 24,352,003 as the receipt's
projections.fixed_schema_products.binance_usdm_harmonic_bundle.projected_bytes.
The pinned Receipt 258 actually records 1,133,590 measured current bytes and 150,331
projected rows there. The 24,352,003 value is instead
partitioning.largest_future_width_charge_candidates.harmonic_bundle, a future-only
charge. Its terms are 150,331 * 8 reference-index bytes, 22,850,312 future partition-field
bytes and 299,043 bytes from the three bundle reference dictionaries. The existing
current-plus-future provision is therefore 25,485,593 bytes. See sizing source
future_bundle_field_bytes and largest_future_partition_candidates.

Retain 24,352,003 as this assignment's conservative actual bundle-file cap, within
that existing provision. Do not expand capacity, rewrite sizing or spend the operating
reserve. Authenticate the real receipt keys and arithmetic; do not compare the
1,133,590 measured-current term to the 24,352,003 cap as if they were the same field.
Correct source comments, resource reporting and fixture receipts accordingly. A
fixture that rewrites projected_bytes to 24,352,003 conceals this reviewer error.

## Consolidated blocking findings

1. **Real descriptor and lineage formats must work.** In the assembler,
   _table_file requires every artifact to declare native_symbol. The accepted OI
   quality_gap_artifact is a global artifact without that key. Accepted liquidation
   gap descriptors also omit native_symbol and utc_month while their authenticated
   paths/lineages identify them. The tests supply an artificial bar quality artifact
   with both fields and omit the real variants. Handle those accepted formats
   explicitly, without inventing a symbol or silently dropping a gap. _mapping_count
   only recognizes mappings/upstream/mapping_count and otherwise returns zero;
   accepted membership lineage uses evidence_records and OI lineage uses raw_objects.
   Derive and validate the actual lineage count/bindings for each supported format,
   including product/component/symbol/partition hash/rows/schema where declared.
   Reconcile declared main/gap/component totals, preserve the disclosed cost variance,
   and do not substitute sizing placeholders for the actual constituent inventory.
   Do not require the actual bundle row count to equal an estimated sizing row count
   without reconciling their constituent definitions against the accepted completions.

2. **The current reads and bundle construction are not bounded streaming.**
   _read_bytes appends every block and joins the whole file even when _resolve asks
   only for a Parquet hash. That retains whole accepted data files. Separate streamed
   file hashing from bounded metadata reads. Supply finite limits before allocating
   sizing/qualification/manifest/proof metadata; Receipt 258 itself is 39,727,059 bytes.
   _write_bundle constructs every row/column and the whole Arrow table before passing
   row_group_size=65536. Use a ParquetWriter with batches of at most 65,536 rows;
   setting a row-group argument alone is not the required construction bound. Metadata
   indexes may be retained only under explicit finite bounds. Preserve deterministic
   ordering and byte-identical replay.

3. **The consumer contract must establish logical readback, with an explicit proof pin.**
   _verify_proof currently requires source_value_sha256 and roundtrip_value_sha256 to
   equal the original physical Parquet SHA, value_identity=byte_identity, and both
   time endpoints null. This accepts copied-file bookkeeping and cannot establish
   typed-row/time/value equality through Nautilus serialization. Keep the physical
   source identity separately. Define a deterministic typed-value digest contract
   covering complete ordered rows, exact decimals/nulls and timestamp precision;
   require equal source/readback row counts, logical digests and time extrema where
   the frozen table has time fields. Null time bounds require an explicit applicable
   reason such as an empty or non-temporal component. Metadata is authenticated as
   metadata, not claimed as a Nautilus table. The later checker remains outside this
   drop. Add a required caller-supplied proof SHA to publish/verify APIs and CLI and
   compare it before admission; hashing whichever file --proof names is not an
   approval pin. Ensure finite proof bounds can represent the complete real inventory
   and charge its persisted bytes. Test equal values in different Parquet encodings,
   changed decimal/time values, missing components, sample scope and wrong proof pins.

4. **Bind code_commit to committed source.** seal_code_identity accepts any correctly
   formatted commit and only compares runtime files with the working tree. It never
   authenticates those five files against the supplied commit's blobs. In production,
   verify the actual committed bytes of all five paths as well as the three executing
   runtime files; reject dirty/missing/wrong blobs and nonexistent commits. A read-only
   Git invocation implemented in production code is allowed; this does not authorize
   the source actor to run repository Git commands. Preserve the private fixture seam
   and relocation-independent identity. Exercise this binding with temporary fixtures.

5. **Seal and recheck the complete release chain.** _load_prepared checks only list
   length, identity and transform, not eleven unique required types/IDs or the exact
   bundle dependency graph. Repeating one entry eleven times passes that loader;
   _classify and the reader's set comparison can then treat a one-dataset catalog as
   complete. Enforce the exact ten constituents plus bundle, uniqueness, common
   code/config/transform, valid table-versus-metadata accounting, no supersession,
   and bundle edges to precisely the ten constituent IDs. Prepared/publication entries
   must also pin exact physical manifest bytes and bookkeeping: manifest identity
   excludes publication.created_at/publisher. Recheck descriptor and manifest snapshots
   with data references before admission, so changing excluded bookkeeping or replacing
   a manifest during admission cannot escape the proof binding. Verify the entire
   publication entry bindings, not just a set of IDs/types. Keep the existing one
   BEGIN IMMEDIATE insertion, complete replay comparisons and BitMEX exclusion checks.

6. **Do not mutate ancestors or strand replay behind a crashed stage.** _bundle_root
   chmods before checking symlinks; _open_directory fchmods every existing ancestor,
   including data, to 0700. Validate before mutation and restrict mode changes to newly
   owned output objects/directories. Keep validation and hashing attached to the opened
   file/directory descriptors; do not reopen a winner through its /proc pathname.
   Check stable file identity before/after hashing. The fixed .<name>.tmp created
   outside the try block can survive process death and block all future attempts.
   Use uniquely owned staging and no-clobber finalization/reuse without deleting other
   attempts' evidence. Validate the actual catalog path/connection binding too; reject
   symlinked or mismatched databases. Strict readback must open an existing catalog
   read-only and inspect one consistent SQL snapshot, without creating a missing DB
   or committing/rolling back caller-owned work.

7. **Enforce actual resource preservation before writes and admission.**
   _enforce_resources compares estimates to constants but never checks free capacity;
   setting operating_reserve_bytes to the expected constant does not preserve it.
   _resource_totals' 4096*(datasets+files+dependencies+8) is not a demonstrated bound
   for actual SQLite/index/overflow/WAL growth. Account for new manifests, descriptors,
   proof, owned stages, existing candidate leftovers and database/WAL/temp growth using
   measured bytes or a justified conservative reservation. Check capacity on the
   relevant filesystems before writing and before visibility; retain 29,690,701,415
   reserve bytes and the 4,985,471,619 metadata remainder. Accepted data is not charged
   again and unused coverage reservation is not transferable. A failed bound must
   leave no newly consumable rows and report its exact blocker.

8. **Make the tests reach the required failures.** Nested _ready/_fixture calls use
   mkdir without parents. The conflicting-writer case constructs identical data in a
   relocated root, hence identical IDs, then calls its second writer sequentially and
   expects a conflict. Use genuinely conflicting candidates and actual concurrent
   starts; preserve relocation invariance for identical inputs. The pending-transaction
   case uses an idle default-mode connection, not pending caller work. Create an actual
   uncommitted sentinel and prove refusal preserves it. Add a mid-insertion SQL failure
   to prove rollback after some rows/files/edges have been inserted; a failure before
   BEGIN does not test that. Use representative real completion/lineage shapes and
   frozen Arrow contracts with independently expected values, rather than one-column
   schemas and generated expectations copied from production helpers. Cover the above
   proof, manifest-chain, dirty-code, path, crash-replay and capacity regressions. Keep
   all fixtures temporary; no real data run or external consumer installation.

## Corrective return and one targeted test exception

After completing the correction, the selected senior may execute exactly once:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

This is the AGENTS.md targeted senior test exception for immediate corrective source
feedback. Stop on its first nonzero result, report the exact command/output, and return
without further edits or retries. On success, return the five hashes/line counts and
concise implementation notes. No Ruff/control/acceptance suite, real prepare/publish,
data mutation, install, network, subagent, records, Git, commit or push is assigned.
Hermes retains integration, complete validation, evidence and Git ownership. Neither
this targeted result nor source review accepts the release or authorizes another ticket.

Reviewer governance publication scope is exactly this Review 493, Review 492's sizing
clarification, docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. Developer files are
excluded from reviewer staging/commit/push.
