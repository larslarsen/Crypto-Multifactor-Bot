# CEX-002 Review 492 — Bundle and reference catalog source

Reviewer: Lead Quantitative Finance Researcher/Engineer
Senior source actor: Grok Build, native grok-4.7 High
Ticket: CEX-002, IN_PROGRESS; next ticket NONE

## Accepted starting point and routing

Review 491's six-file correction is integrated and pushed at
f574ec1343834217c9f3baca40a0862a829b0e00. The reviewer verified every committed blob
against its approved hash and the exact six-path commit, with HEAD equal to origin/main
and an empty index. Record 490's single extra EOF newline was removed after the first
staged whitespace failure; the corrected staged check and normal push passed. No tests
or real comparisons were repeated for that formatting correction.

Ten products and the bounded minute/hour reconciliation remain accepted. Use Grok for
the next substantive senior drop: it just delivered the accepted opening-price fix,
source-authority/transaction work requires a senior, and the owner reports substantial
expiring Grok usage. GPT-6.1 Sol remains reviewer and does not author production/tests.

ADR-0037 records the necessary reference-publication adapter within ADR-0024's work
order. This is the next source drop for the same ticket, not another acquisition plan,
schema generation, experiment or trading engine.

## Exactly five writable developer paths

1. src/cryptofactors/catalog/dataset/cex002_reference_release.py
2. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
3. scripts/research/publish_binance_usdm_harmonic_bundle.py
4. tests/catalog/test_cex002_reference_release.py
5. tests/ingest/test_binance_usdm_harmonic_bundle.py

Existing source/tests, migrations, dependencies, exports, records and data are read-only.
No existing generic catalog/publisher change, SQL migration, hard links or data copies.
Keep catalog code independent of ingest code; the ingest assembler calls the catalog
adapter. Use existing manifest models/canonicalization and protected catalog insertion
helpers where useful, without per-dataset commits or public verifier bypasses.
Honor the layer matrix: catalog imports only catalog/core project modules; ingest
imports only ingest/catalog/core project modules. Read acquisition constants as source
references, not new runtime imports. Obtain frozen Arrow contracts from authenticated
receipt schema data or existing ingest modules' declared schema interfaces. Do not add
a forbidden acquisition import, a dynamic-import escape or a schema facade elsewhere.

## Frozen real inputs

Use the nine product roots/completion hashes in scripts/research/reconcile_binance_usdm_coverage.py
ROOTS, identical to binance_usdm_coverage.COMPLETION_SHA256. Add the tenth product:
data/.cex002_coverage, completion
9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151.
The root is .cex002_coverage, not .cex002_coverage_gap.

Qualification: research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json,
SHA f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09.
Sizing: research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json,
SHA 3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589.
Holdout: data/cex002_qualify/cex002_holdout_boundary.json,
SHA 2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85,
ID c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2,
UTC 2026-08-21T16:19:08.994166+00:00.

Accepted minute/hour completion:
data/.cex002_kline_reconciliation/.complete/e3c8f9f5ade1b92069b97e6b83931c345886d40901b85b1c4106604edd9b5e5c.json;
report 96ae8db169666598643ac4e2f9aa2136b77c0dbeeaa90d2a3e4e4de9e983c89c.
Require their exact bytes/bindings and PASS, 2,672/2,672 fields, 167 hours, nine days,
ten roles, empty discrepancies/coverage failures/unexplained absences. Preserve the
earlier FAILED report; do not select an arbitrary first report from a directory.

Coverage completion pins six manifest pages: daily, summary, source_gap, typed_gap,
quality_gap and excluded_membership. Follow its declared paths/hashes; it does not
have the same layout as ordinary product.partitions. Cost has five component schemas,
plus frozen_source_gaps; price-state/OI/other products have their own declared gaps.
Do not infer one descriptor shape or one schema for every product. Read the accepted
normalizers/coverage checker to handle the real formats directly.

Coverage facts: 771 accepted native identities, 73 funding-only, 237 excluded
classifications; 1,971,447 aligned day rows; 428,090 observed five-product days with
digest f0c0d7c21fc68d2d454b07ec969b6d794f380e22e751c643dee09184e3896665;
424,431 full-cadence days with event presence, digest
22219a5a243fcf1fda3ab5deacd99fbe72869375021d9d2f2a98868580e48fab.
Keep both definitions. Funding expected count is null; liquidation_complete is false.
Cost's 136,532,583 ticker-row projection excess and ordinary_sizing_check_passed=false
remain explicit accepted evidence, not a reason to fabricate rows or silently fail
an otherwise matching accepted completion. Do not rewrite sizing.

## Implement the complete bounded source drop

1. Provide preparation, final admission and strict readback/verification APIs plus a
   CLI with explicit prepare/publish/verify actions. Preparation creates only new
   content-addressed files under data/.cex002_harmonic_bundle and never catalog rows.
   Production uses frozen inputs above; private fixture policy injection is allowed,
   never a CLI authority override. Explicit --repo, --catalog and --code-commit inputs
   must be validated. Production code identity must bind the committed blobs of this
   drop to actual runtime source bytes; refuse dirty or mismatched code. Keep canonical
   identities independent of wall-clock execution time and absolute repo relocation.
2. Produce ten canonical reference product manifests and the actual BUNDLE_COLUMNS
   Parquet matching final_product_schema(PRODUCT_BUNDLE) exactly; the authenticated
   receipt's non_archive_product_schemas contains that full Arrow contract. Rows describe actual constituent
   table partitions/components with real dataset IDs, hashes, byte/row counts, lineage
   mapping counts and schema/source/config identities. Preserve native identity and
   canonical-null state, all gap categories, units, scenarios and censorship. Metadata
   reports/lineages/receipts are pinned in manifests/descriptors, not fabricated as data
   rows. The eleventh canonical manifest describes the bundle and depends on all ten
   constituent dataset IDs; no recursive self-row or invented publication field.
3. Authenticate complete declared file sets, canonical manifests, lineage references,
   regular contained paths, physical hashes/bytes, exact Arrow schemas and footer rows.
   Reconcile per-component main rows, gap rows and descriptor totals. Reject missing,
   empty-required, extra/unaccounted, corrupt, wrong-schema or mixed-authority inputs.
   Reuse accepted economic evidence; do not rerun normalizers or claim missing final
   economic checks have passed. Bound metadata indexes explicitly, stream hashes in
   finite chunks, write bundle batches at most 65,536 rows, and never load full accepted
   price/OI/cost data tables. Catalog code independently verifies external references;
   it must not trust a caller's verified=true boolean or a fabricated generic receipt.
4. Complete ADR-0037's prepare/consumer-proof/final-descriptor chain. Preparation is
   explicitly non-consumable. Final publish requires caller-pinned consumer proof and
   checker-source hashes from a later reviewer-authorized run, with the proof bound to
   the exact prepared descriptor and Nautilus version. Define and test a strict v1
   proof contract: document_type, version, PASS, candidate hash, checker hash, package
   version and complete per-dataset/component file/row/time/value reconciliation.
   Missing entries, unequal source/roundtrip values, sample-only scope, unsupported
   semantics or a bare PASS must block. Do not generate a real consumer proof or
   claim Nautilus support was executed. That checker is a subsequent bounded drop.
5. On admission use an idle connection and BEGIN IMMEDIATE. The five targets in
   bitmex_funding_quarantine.BITMEX_FALSE_AUTHORITY_TARGETS must still be REJECTED/REGISTERED, carry the accepted
   quarantine marker and remain ineligible; verify their catalog/file snapshots without
   rerunning quarantine or changing them. Recheck authenticated input file identities
   before commit. Insert all eleven dataset rows, complete file rows and bundle
   dependencies in one transaction, then commit once. On any failure rollback all new
   rows. Identical replay compares every persisted field/file/dependency and reuses
   only a complete identical winner. Reject partial/conflicting rows and pending caller
   transactions; never repair, supersede or commit another caller's work. The durable
   final descriptor precedes SQL commit; no post-commit marker is needed for visibility.
6. The CEX reader follows an explicit publication identity, proves all eleven manifests
   and their common descriptor/proof/catalog bindings, and reauthenticates referenced
   inputs. Prepared, absent, stale, incompatible, partial or mixed releases must fail.
   Preserve generic catalog behavior, including exclusion of the five invalid datasets.
7. Enforce existing resource allocations before visibility. Receipt 258's harmonic
   bundle allocation is 24,352,003 bytes; derive and explain the exact receipt terms.
   Remaining release metadata reservation after coverage is 4,985,471,619 bytes;
   coverage's unused reservation is not transferable. Count new manifest/descriptor,
   SQLite/WAL and temporary bytes without charging accepted data again. Preserve
   29,690,701,415 operating-reserve bytes. No silent capacity expansion or reduced scope.
   On bounds failure leave only non-consumable evidence and report the exact blocker.

## Test source and return boundary

Author meaningful temporary-fixture tests for real descriptor-shape variants, exact
frozen schemas and bundle values, complete artifact accounting, cost's disclosed row
excess, separate intersection definitions, lineage/identity/authority corruption,
unsafe paths, missing/wrong consumer proof, schema/row mismatch, byte-identical replay,
changed input during admission, concurrent identical/conflicting writers, interruption
before/after SQL commit, pending external transactions, full rollback/default-resolver
invisibility, and strict reader rejection of partial or mixed releases. Tests must use
independent expected values and exercise the adapter against existing catalog migrations.
Do not change or expand generic catalog tests/source to make this protocol pass.

Read the bounded governing documents and named read-only source references, then write
the five paths. No subagents, tests/acceptance commands, executable discovery probes,
real data run, network acquisition, installation, records, Git, commit or push. Return
the five path hashes/line counts and concise implementation notes, then stop for source
review. Hermes owns validation, integration and any later real prepare/publish commands.
No final data/catalog publication or next ticket is authorized by this source assignment.

Reviewer governance publication scope is exactly this Review 492, ADR-0037,
docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. No developer integration belongs
to the reviewer exception.
