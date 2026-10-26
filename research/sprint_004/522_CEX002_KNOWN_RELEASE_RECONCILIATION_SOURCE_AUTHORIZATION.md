# CEX-002 Review 522 — Bounded known-release reconciliation correction

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Source actor: existing Sr Dev — Codex Sol, GPT-6 Sol High, sole senior
Architecture: ADR-0040; original ADR-0037 / ADR-0039 contracts remain frozen
Next required actor: Sr Dev — Codex Sol, source correction only

## Fixed starting point

Review519 accepts successful initial admission and Record521 terminal disclosure at
b2c485ce86bb8d93e059e96439c3c4e63352edc6. The generic replay failed after
32,935.614 seconds at a late operating-reserve guard; its full reader never ran.
Review517 accepts the full Nautilus proof after 189,195.734 seconds. Preserve both
successful results and the genuine failures. No existing full pass is repeated.
The owner explicitly requires tracking progress and avoiding another wasted run.

The reviewer selects the existing GPT-6 Sol High source actor: it delivered the
accepted original catalog/codec corrections and is suitable for this bounded
source-authority/transaction-sensitive task. GPT-6.1 remains reviewer, not source
or test author. Reuse this existing actor; no new or concurrent senior. Hermes is
stopped and is not authorized for new helper authorship or execution yet.

## Exactly two writable developer paths

- scripts/research/reconcile_cex002_admitted_release.py
- tests/test_cex002_admitted_release_reconciliation.py

Everything else is read-only, including the original catalog/assembler/CLI/checker,
accepted data, source/test files, governance/evidence and Git. No public exports,
dependency/install/config/SQL-schema change, new prepare/admit, cleanup or live run.
The new command is a research tool in the same role as the external consumer checker.
It may import original catalog models/authority/path/schema/identity/classification
helpers; never monkeypatch them or bypass layer boundaries. It must independently
implement the new accepted-proof reconciliation logic, not call the slow full-row
verifier under a new name. No application/production source changes are permitted.

## Exact production authorities

Original three-source commit: 1f5629badfa0e8af6338fbeb019a5f7e60b6a324
Candidate SHA256: 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34
Publication SHA256: 5ea22270b71064c94c4f6dc60f3f045219742a3130cfdb1293b6cbe47a99a30d
Proof SHA256: 3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d
Proof bytes: 264156517
Consumer checker SHA256: ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117
Nautilus version recorded in accepted proof: 2.0.0rc3
Expected: 11 datasets, 423446 components/files, 178947 tables, 244499 metadata,
1165116869 physical table rows, ten dependency edges, zero raw-input edges.
Catalog: existing exp003.db, never a fresh database or catalog reconstruction.

The CLI accepts explicit --repo, --catalog, --source-sha for the new command's
own source identity. Production authorities above are fixed; no --proof/candidate/
publication overrides, --skip-verify, trust flags or resource-bound overrides.
Private fixture policy injection into an internal/API function is allowed only for
synthetic tests and must be inaccessible from the production CLI. Every real run
uses the existing project .venv/bin/python, not the isolated consumer environment.

## Complete behavior

1. Fail early on insufficient free space using the unchanged 29,690,701,415-byte
   operating reserve and the original release charge/SQLite reservation/resource
   arithmetic. Metadata remainder 4,985,471,619; proof cap536870912; publication
   allowance8388608 remain fixed. Recheck before any catalog transaction. No large
   temporary files or duplicate proof copies. Metadata/proof memory is bounded by
   explicit existing caps/counts; no whole-product row lists.

2. Authenticate exact pinned candidate/final-publication/proof bytes and strict root
   contracts, original runtime source identity and checker bytes, eleven canonical
   manifest identities/order/dependencies and all common authority bindings. The
   publication must already be consumable and point to the exact candidate/proof.
   Refuse a prepared-only, unknown, substituted or mixed publication. Use complete
   accepted file closure; do not infer descriptor layouts from arbitrary files.

3. Validate the entire strict v1 proof against that fixed accepted proof SHA and
   manifest closure: exact component key sets, unique paths, accepted kind/schema
   tags, physical hashes/bytes, source/readback row counts and equality of value
   digests/time semantics, metadata zero-row/byte identity, total counts and native
   bar primary versus gap distinctions. Reuse the accepted logical value/time
   results as such; never fill a readback result from freshly read source values.

4. Freshly authenticate EVERY referenced regular contained nonsymlink file and its
   parent safety, physical SHA256/size, and table footer/schema/row count. Preserve
   strong snapshot binding and original _recheck behavior at transaction boundaries;
   do not substitute stat/mtime caching for bytes. A fresh hash against the accepted
   proof's source hash establishes unchanged source values. No Arrow iter_batches,
   read_table, logical-row loops, reference_proof_component, _verify_proof,
   publish_release or read_release invocation in this real path. Do not alter those
   original functions. Footer-only reads are required; the previous billion-row
   logical calculation and Nautilus write/query are expressly excluded.

5. Authenticate the original five quarantined BitMEX rows and their continued
   exclusion using original helpers. Reconcile the existing complete catalog using
   original _classify/_same_release semantics. Derive and compare exact ordered
   all-column dataset/file/dependency/raw-input snapshots, including timestamps,
   against the eleven authenticated manifests and common publication. Refuse absent,
   partial, conflicting, extra or consumability-incompatible rows. Do not insert,
   update, delete, migrate, recreate, supersede or repair anything.

6. Demonstrate known-release identical replay in an owned idle connection using
   original BEGIN IMMEDIATE / full file-and-quarantine recheck / identical
   classification / ROLLBACK behavior. Follow with a separate original read-only
   snapshot/classification/consumability check for all eleven IDs. Reject pending
   caller work without committing or rolling it back; verify catalog connection
   binding. All dataset/file/dependency columns and publication identity remain
   identical across phases. Any non-identical state fails, never admits data.
   This is ADR0040's explicitly bounded checkpoint replay/readback, not a fabricated
   successful exit status for the old generic CLI or an initial-admission fast path.

7. Emit structured stderr progress at least every five seconds during controllable
   file/hash loops and at every phase boundary: stage, files/bytes verified, expected
   totals and elapsed time. Include bytes during large-file hashing so a single
   large file cannot hide hours of work. Preserve original safe hashing semantics;
   progress code must not weaken checks. Enforce a 30-minute real-run deadline via
   a monotonic internal budget checked in loops; a later Hermes command will also
   have an external 1800-second timeout. The audit emits no proof/data files. Final
   stdout JSON reports all pins/own source hash, exact real counts, resource facts,
   catalog snapshot digests and PASS scope accepted_proof_unchanged_bytes_and_catalog.
   Clearly distinguish reused accepted row-value evidence from freshly hashed files;
   do not claim new logical-row computation or a new Nautilus consumer PASS.
   Fail with concise structured stage/error/progress and nonzero status, preserving
   evidence. No automatic retry, stale resume cache or cleanup.

## Meaningful tests and one targeted source-feedback command

Use tiny private real-file/catalog fixtures and the original strict consumer-proof
component/verifier in TEST construction/comparison where needed to establish
compatibility. Demonstrate a real unchanged successful replay/readback of an
already admitted tiny release, exact no-change catalog snapshots and rollback,
without executing logical-row reads in the NEW command. Fail-closed cases include
changed source bytes with the same schema/count, changed accepted proof bytes,
wrong candidate/checker/publication bindings, duplicate/missing component paths,
wrong footer/schema/counts, symlinks/unsafe ancestors, source replacement between
hash and transaction, catalog partial/conflicting/extra rows or changed bookkeeping,
quarantine drift, pending/foreign caller connections, reserve failure BEFORE source
traversal, deadline failure and proof/metadata bounds. Ensure no new dataset/file
rows are inserted even on error. Test that normal generic validation behavior stays
unchanged and the production CLI cannot select fixture/arbitrary authority pins.

After the complete two-path correction, the targeted senior test exception authorizes
exactly ONE execution for immediate source feedback:

```
PYTHONPATH=src .venv/bin/python -m pytest tests/test_cex002_admitted_release_reconciliation.py -o addopts='' -q --tb=short -ra
```

Stop on the first nonzero result; no fix/retry or other validation/import/compile/
lint/control/test command. Bounded read-only source, JSON/descriptor/schema inspection
is allowed for design; no full-data scan or existing production-function execution
against real inputs. Return both path hashes/line counts, exact test command/output/
status and check map, then STOP for reviewer. No Git, records, real audit or catalog
transaction. Reviewer independently inspects the entire drop before Hermes validation,
integration and one separately authorized, actively monitored bounded real run.

## Reviewer publication whitelist

- research/sprint_004/522_CEX002_KNOWN_RELEASE_RECONCILIATION_SOURCE_AUTHORIZATION.md
- docs/adr/0040-cex002-accepted-proof-reuse.md
- docs/handoff/CURRENT_TASK.md
- tickets/CEX-002.md

No source/test/evidence/data integration by reviewer. The ticket remains CEX-002
IN_PROGRESS; next ticket and authorization remain NONE. This is its bounded
reconciliation correction, not a new ticket or expanded acquisition/research scope.


## Additional fixed admission snapshot anchors

For complete all-column catalog binding, production must also match the accepted
post-admission Record521 snapshot (record SHA256
33f6f74a9d53699a11c7a9249b3b61000f01f882e229fe2e6384bbbca5eb7528):

| Table | Rows | Accepted snapshot SHA256 |
| --- | ---: | --- |
| dataset | 11 | 04d27a4fc58f80189889df81e3e78a196c33ee7d0d7a98cb497b72bb15993f5d |
| dataset_file | 423446 | c37bdb87f6925f0c6441ed6bf2b1751904b6b7ddab4dd0f054154b871f9c9855 |
| dataset_input_dataset | 10 | 9f4fbf2eec784f2b801f709b4b27ab24b7f0388ad4ad3d22e6d24640d6e2f322 |
| dataset_input_raw_object | 0 | 6a8d487a15f8d0927d64f2c03491325ce88b37d29ed7402743c05bd67f210de3 |

Use the EXACT query/order/all-column serialization from Review519's committed
snapshot function that produced those values; inspect the actual Python string
escaping rather than assuming a delimiter. Bind column order as well as rows.
Require these trusted production anchors in addition to before/after invariance and
original manifest classification. This detects a change predating this checker,
including bookkeeping/extra-column changes, rather than only changes during it.
Private fixture policy may provide its own independently constructed tiny snapshot
anchors; the production CLI has no override. Missing/wrong snapshot anchors fail.
This strengthens requirement5 without changing either writable developer path.


## First targeted source feedback — bounded correction

The senior executed the sole assigned pytest once: exit1, 21 passed and 2 failed
in4.25seconds. Source at that stop: 594lines / SHA256
818d05690bbdc8b66e6b8ee289195b6a599a30bead59b523239b8e5d1df980f9;
tests414lines / SHA256
1dcc84e5a38fcf8b1bd1476d97b747c929a5a844ee2c037c40323da449a708a8.
The candidate-pin refusal raised the correct missing-path UnsafePathError but its
test expected another family. The independent empty-raw-table snapshot oracle
returned fcce0904… for a literal backslash-n delimiter, while the immutable accepted
Record521 digest is6a8d487a… . The senior stopped without edits or retry.

The reviewer's earlier interpretation of the saved command escaping was wrong.
The accepted digest oracle is authoritative: the actual recorded snapshot uses a
newline byte as delimiter. Correct the new implementation and independently coded
fixture serializer to newline; NEVER change the accepted6a8d… oracle or production
anchors to match a different implementation. No real reconciliation has run.

Authorize only this correction in the same two paths, plus these already reviewed
test-quality items: candidate-pin refusal expects its specific UnsafePathError;
test CLI refusal by executing argument parsing for forbidden overrides, replacing
source-text assertions; trap pq.read_table/ParquetFile.iter_batches and the original
logical proof helper during the successful tiny-fixture audit. Generic reader
compatibility is checked after removing those traps. Keep all previous cases and
actual original known authorities. Make cumulative hash-progress counters clearly
identified as hash operations/bytes across passes or provide phase-local counters,
so monitoring does not mislabel repeated safety rechecks as unique completion.
No other source behavior, original-module edit or widened authority is assigned.

After all corrections, authorize exactly ONE additional execution of the SAME
focused pytest command printed above. First nonzero stops without edits/retry.
Return final hashes/line counts and exact output/status; no real audit, other
validation, Git, integration or record authoring. Hermes remains stopped until
reviewer accepts this final source and separately enumerates its workflow.
