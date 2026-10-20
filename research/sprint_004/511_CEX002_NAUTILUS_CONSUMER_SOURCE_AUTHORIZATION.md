# CEX-002 Review 511 — Clean Nautilus consumer checker source

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Architecture: ADR-0037 /0038 /0039
Disposition: one bounded two-path source/test-source drop; no execution or integration

## Accepted starting point and routing

Review 507 accepts Record 510 at 16765eedc87eba67bbe18cda90afaf5301d6b28d and
candidate 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.
The source integration is 1f5629badfa0e8af6338fbeb019a5f7e60b6a324. The existing
eleven manifests reference 178,947 tables and 244,499 metadata components, totaling
423,446 files and 1,165,116,869 physical table rows. Ten dependency edges bind the
bundle; its Parquet has 178,946 rows and 13,232,150 bytes. No catalog admission or
consumer proof exists. Preserve all accepted source/tests and real artifacts.

Select the existing GPT-6 Sol High source actor: it authored the accepted strict
proof/catalog interface and delivered the accepted schema correction (63 focused,
162 integration cases). That context and accepted-result evidence fit this senior
serialization/authority work. Spark's mechanical scope is insufficient. GPT-6.1
remains the stronger reviewer and authors no production/test source. Continue the
owner-approved direct delegation/feedback route, with one senior actor only.

## Exactly two writable developer paths

1. scripts/research/check_cex002_nautilus_consumer.py
2. tests/test_cex002_nautilus_consumer.py

Everything else is read-only, including existing catalog/assembler source, dependency
files, producer tests, governance, accepted artifacts and the Harmonic_Trader repo.
Implement the runtime checker in the one script so its complete new runtime source
has one caller-pinned SHA. Reuse protected catalog metadata/pure codec interfaces
where appropriate; do not import/run normalizers or replace catalog authority.

## Fixed runtime compatibility

Target nautilus-trader==2.0.0rc3 and pyarrow==25.0.0 on Python 3.13. The reviewer
verified these installed distribution metadata and current PyO3 .pyi APIs under
/home/lars/Harmonic_Trader/.venv/lib/python3.13/site-packages. Read these stubs and
the existing read-only integration/nautilus_data.py there for registration patterns;
do not assume the legacy persistence.catalog.parquet import path exists. Current
APIs include model.CustomData/DataType/register_custom_data_class and
persistence.ParquetDataCatalog.write_custom_data/query_custom_data/write_bars/query_bars.
Inspect signatures rather than guessing. No dependency install or API probe is
assigned to the developer. Hermes later owns an isolated pinned test environment.

## Complete checker contract

1. Provide a CLI with explicit repo, candidate SHA, checker-source SHA and fresh
   owned scratch-root arguments. Production accepts only the candidate/source
   identities above and the pinned library versions. Use only metadata named by
   that descriptor; reject bounds markers, partial/mixed manifests, wrong chain,
   extra/missing/unsafe refs, source/code drift, changed schemas and symlinks.
   Existing _load_prepared and seal_code_identity may be reused for their bounded
   read-only roles. Dataclass statistics are under .statistics; file kind/schema_ref
   under .partition; registries under .quality_summary. Do not rerun assembly.
2. Authenticate every referenced regular contained file's hash/size and every table's
   actual ordered Arrow schema, nullability and footer rows against its resolved
   shared registry. Stream source values in bounded batches; never load a whole
   cost/OI table or release into a row list. Metadata is byte-identity with rows 0,
   non_temporal_component and metadata_bytes, matching the existing proof contract.
   Detect source/manifest/candidate changes during the check and before sealing.
3. Implement ADR-0039's real Nautilus roundtrip for ALL table rows/components,
   including typed gaps, membership, coverage tables, cost components and bundle.
   A registered lossless row envelope must actually be written into and queried
   from a fresh catalog; derive returned values/digests from those queried objects.
   Native bars must additionally pass exact native Bar write/readback for OHLC,
   volume, native identity and close time. Do not count source reads, paths, digests,
   fixture mocks or an import/version string as a Nautilus roundtrip. No sample mode
   or full-release PASS from a subset. Metadata JSON does not become fictional rows.
4. Preserve decimal128(38,18), signed/zero values, nulls, dictionary logical values,
   lists, all schema field order, and ns timestamps without datetime truncation or
   float conversion. Do not round through ambient Decimal context. Native conversion
   is exact or fails. Keep source availability unknown, canonical IDs null, fees/gaps,
   indicative unavailability and observed/censored liquidation semantics unchanged.
   ADR-0039 validation clocks never become source-availability evidence. Reconcile
   explicit row ordinals to detect reordering, duplicate, omitted and changed returns.
5. Emit the EXACT existing strict v1 proof (PROOF_KEYS/COMPONENT_KEYS, complete_release,
   candidate/checker SHA, actual Nautilus version, eleven dataset IDs in chain order,
   every component exactly once). Source and readback typed-row hashes/time bounds
   must independently reconcile and match reference_proof_component's wire meaning.
   Sharing pure token encoding is allowed; assigning the source digest to the
   roundtrip field or using reference_proof_component as fake readback is forbidden.
   Tests may use that helper as a reference. Proof generation may not mutate catalog,
   invoke publication or alter any accepted input. No proof-schema/digest change.
6. Keep at most 65,536 rows and a finite byte budget in a processing batch; bound
   returned catalog lists too. Use smaller byte-bounded batches when necessary.
   Scratch may use at most 268,435,456 physical bytes under the fresh owned root,
   including native/custom catalogs and sidecars. Check finite prewrite estimates
   and measured usage, preserve the 29,690,701,415-byte operating reserve, and refuse
   unsafe or unexpected paths. Delete only authenticated files created by this run,
   after their successful readback; never arbitrary recursive cleanup. Failure
   preserves partial state and exposes no successful proof. No automatic repair/retry.
7. Stream the proof with a 536,870,912-byte cap, not a second whole-release in-memory
   component list. Seal atomically/no-clobber as a content-addressed regular file in
   data/.cex002_harmonic_bundle/.proofs only after full success. Bound stage bytes and
   account for every owned byte and SQLite reserve. Current preparation charge is
   3,686,198,800; full proof/publication allowances total 4,231,458,320, leaving
   754,013,299 under the fixed 4,985,471,619 remainder. Scratch 256 MiB fits that
   headroom; no budget/multiplier change or uncharged external duplicate proof.
8. Emit concise structured stderr progress with completed files/rows, elapsed time
   and stage, plus final proof path/SHA/counts/version/resource totals. At this scale
   throughput and bounded memory matter: avoid redundant source rereads solely for
   accounting, and hash values actually returned by Nautilus. No claimed throughput
   or runtime without measurement. Stop for reviewer direction if the pinned API
   genuinely cannot preserve a required type; do not silently bypass it.

## Test-source requirements and stop

Author real pinned-Nautilus tests for lossless custom and native bar roundtrips,
precision-38/signed decimals, nulls/dictionaries/lists/ns clocks, zero-row gap tables,
all component kinds and strict complete proof compatibility. Include omitted/duplicate/
modified/reordered readback, unknown availability, source tampering, schema/candidate/
checker/version mismatch, unsafe paths, bounded batching/scratch, failure/interruption
without PASS, no-clobber collision and owned-only cleanup. Reordered rows may be
reassembled only with their authenticated ordinal; substitution must fail. Use tiny
private fixtures; the production CLI must not expose authority/backend overrides.
Core NT tests require the actual package and may not silently skip in acceptance.

Return the complete two-path drop, SHA-256/line counts, required test-environment
dependencies and any exact pinned-API limitation. Developer performs NO tests, test
commands, imports/API probes, real-data execution, data creation/cleanup, installation,
network, implementation records, Git, integration, commit or push. Read-only source/
stub inspection is allowed. This is a new checker, not the corrective-drop targeted
test exception; Hermes owns its first execution after reviewer source disposition.
Stop for source review. No real consumer/proof run, admission or next ticket is assigned.

## Reviewer governance publication scope

Exactly this Review 511, docs/adr/0039-cex002-clean-consumer-transport.md,
docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. No source/test/evidence/data
integration is included in the reviewer's publication.
