# CEX-002 Review 511 — Clean Nautilus consumer checker source

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Architecture: ADR-0037 /0038 /0039
Disposition: source accepted for bounded Hermes validation and integration below; no real consumer run

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

## Parallel Hermes environment setup only

To overlap environment preparation with source authoring, authorize the existing
native free Nous Hermes session for this bounded setup only. This does not authorize
tests, source integration, source edits, data/proof execution or Git publication.
The senior remains the only authorized source actor. Record setup output for the
later integration record; create no implementation-record file now.

Require an empty index, synchronized HEAD/origin, free bytes above the operating
reserve plus 2 GiB, and /tmp/cex002_nautilus_review511_env entirely absent, including
no symlink. Use the existing repository Python 3.13 interpreter. Execute once in
order, stopping on first failure/denial without retry, deletion or repair:

```
uv venv --no-project --no-config --python /home/lars/Crypto_Multifactor_Bot/.venv/bin/python /tmp/cex002_nautilus_review511_env
uv pip install --no-config --python /tmp/cex002_nautilus_review511_env/bin/python --default-index https://pypi.org/simple 'nautilus-trader==2.0.0rc3' 'pyarrow==25.0.0' 'pytest==9.1.1' 'pydantic==2.13.4'
uv pip freeze --python /tmp/cex002_nautilus_review511_env/bin/python
```

Cached packages may be reused by uv; package acquisition is limited to this tooling
environment, not market data. Do not modify either existing project environment,
project dependency/lock files, interpreter configuration, repository source or data.
No --clear, --allow-existing, system-site-packages, manual symlink or installation
fallback. Do not dump environment variables, credentials or package-index config.

Finally run one inline interpreter sanity check limited to sys.executable/version,
importlib.metadata versions of the four pinned distributions, and importing
CustomData/DataType/register_custom_data_class from nautilus_trader.model and
ParquetDataCatalog from nautilus_trader.persistence. Assert Python 3.13 and exact
distribution versions. This is environment compatibility only; do not import or run
the unreviewed checker, pytest, normalizers, catalog admission or any real-data check.
Capture actual commands/output/status/model and stop for reviewer source disposition.


## Final source disposition and Hermes validation/integration

The reviewer accepts the corrected two-path source for first execution by Hermes,
not as a passed consumer check. Static review confirmed actual registered row and
native-Bar readback paths, independent returned-value hashing, exact wire contract,
owned scratch bindings, preserved HOLD failure stages, original writer identity at
seal, final runtime-source reauthentication and fixed resource reservations. The
source author performed no tests/import probes/execution. Original five-file source
hashes remain unchanged. The following final hashes supersede interim drops:

| Path | SHA-256 | Lines |
| --- | --- | ---: |
| scripts/research/check_cex002_nautilus_consumer.py | 438452694111131753d7f8dc34f1ca3fdf5e60377b8bc07564100a5a6f505b0b | 795 |
| tests/test_cex002_nautilus_consumer.py | 184b1e4758e667a9a2f674607ca5735b3c5080fb5cb76da51257573e5787e702 | 431 |

Parallel environment setup is accepted from native session 20261017_134003_4ecfbf,
public messages 99877–99882. All three setup commands exited 0; interpreter is
Python 3.13.14 and the four pinned versions match. The sanity command asserted
Python 3.13 and printed matching versions; it did not assert all four versions,
which the reviewer verified from its output. Preserve this exact limitation.
The uv cross-filesystem cache-copy warning required no operator fallback. Do not
repeat setup or sanity checks. Hermes uses meituan/longcat-2.5-preview:free through
the existing native route with normal approvals.

Hermes now owns this exact ordered workflow, stopping on the first nonzero result
or denial without repair/retry. No source edits, dependency changes, full-data
checker run, catalog mutation, producer, admission or next ticket is authorized.

1. Require empty index and HEAD == origin/main at this reviewer publication.
   Authenticate the two hashes above and preserve all unrelated working files.
2. Execute these commands once in order from the repository root. Private pytest
   temporary fixtures are authorized; accepted release data are read-only.

```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
.venv/bin/python -m ruff check scripts/research/check_cex002_nautilus_consumer.py tests/test_cex002_nautilus_consumer.py
python3 scripts/check_repo_control.py
git diff --check
```

3. If any command fails, preserve its exact command/output/status and all partial
   state, report the failure, and stop. Do not change source, write the success
   record, integrate, retry or repeat earlier passing checks. The reviewer will
   disposition the concrete failure.
4. Only after all commands pass, write
   research/sprint_004/512_CEX002_NAUTILUS_CONSUMER_INTEGRATION_RECORD.md.
   Record source hashes/line counts, actual test count/output/status, lint/control/
   whitespace results, environment setup commands/output and full freeze from the
   preceding session, sanity limitation, actual actor/model, and the fact no real
   full-release proof/admission ran. Do not claim release acceptance from fixtures.
5. Reauthenticate both hashes. Stage EXACTLY those two source paths and Record512.
   Require the staged-name set to equal those three paths and run
   git diff --cached --check. Correct only record whitespace if necessary; source
   repair belongs to the senior. Commit normally with a CEX-002 consumer-checker
   message and push origin main. Require HEAD == origin/main and an empty index.
   Return commit, exact staged names, hashes, test summary and stop for reviewer.

Existing accepted producer/catalog tests are preserved, not rerun. Final whole-repo
acceptance remains pending under the original ticket; this is only the new checker
integration. Any dependency handling for that later suite requires a later bounded
assignment. GPT-6.1 remains reviewer; no implementation/evidence Git duty transfers.


## First execution disposition — bounded string-decoder correction

Hermes's native message 99892 records the exact assigned pytest command exiting 1:
9 failed, 13 passed in 1.03 seconds. All nine failures originate in custom Arrow
field validation during real Nautilus query, before later roundtrip assertions.
The grouped set -e workflow correctly did not execute Ruff, control or whitespace.
No Record512, integration, full-data proof or admission occurred. Preserve output
and partial fixture state. The first-execution source is unaccepted for integration.
The preceding integration assignment is suspended pending corrective source review.

Authorize the same sole GPT-6 Sol High senior for only the same two source/test
paths. The decoder permits logical string variants for payload but requires exact
pa.string for payload_sha256. Correct every declared string field consistently
for pinned Nautilus/DataFusion string/large_string/string_view readback, retaining
strict integer types, exact names, value authentication and wire semantics. Do not
relax unrelated fields or introduce coercion. Use actual error feedback; if another
concrete API issue appears, stop and return it without repair/retry.

Strengthen the late-failure fixture so it asserts each intended injected error is
actually reached and matched; its broad pytest.raises(Exception) currently allows
early decoder failure to masquerade as successful source/code/seal-failure coverage.
Keep the existing real-catalog success tests and all accepted contracts unchanged.

Under the repository's corrective senior targeted-test exception, authorize exactly
ONE execution after these edits, from the repository root:

```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
```

This is immediate source feedback only, not integration/acceptance. Stop at the
first nonzero result and return full exact output/status without edits or retry.
If it passes, return output/count plus final two hashes/line counts and stop for
review. No other commands that execute source/tests/import probes, installs,
records, Git, source paths, real data, cleanup, proof or catalog work are assigned.
Hermes is stopped; GPT-6.1 remains reviewer. Next ticket NONE.


## Corrected source accepted — resume Hermes at lint/integration

The senior's single authorized corrective command exited 0: 22 passed in 1.08
seconds. The reviewer inspected the one-condition decoder correction and precise
late-failure assertions, and independently verified the frozen hashes below. The
real custom and native catalog success tests now pass, and each late failure is
matched to its intended cause. Accept this source for integration; retain the
initial 9-fail/13-pass output separately. The earlier 13 passes did not establish
that late injected failures were reached, which the corrected assertions address.

| Path | SHA-256 | Lines |
| --- | --- | ---: |
| scripts/research/check_cex002_nautilus_consumer.py | 283d1730a2af0d734a52bf03515fec989e591d4dcdbd9cbba81ed727dccad282 | 795 |
| tests/test_cex002_nautilus_consumer.py | 66bd7c1a74e5e420e636acd546e3827360c89ff36720d892057a4aa8fcefa75e | 442 |

The senior is stopped. Hermes resumes the preceding exact validation/integration
workflow at the unexecuted scoped Ruff command, then control and whitespace. Do
not rerun pytest or environment setup: preserve the accepted targeted 22-pass
source result and attribute it to GPT-6 Sol High under the narrow exception, not
to Hermes. Reauthenticate the NEW hashes above and empty/synchronized index before
resuming. The original first-failure stop/normal approvals remain unchanged.

Only after remaining checks pass, finish the originally assigned Record512 and
exact three-path commit/push. Record both test runs with exact commands/status,
source author/test attribution, actual native setup evidence/freeze and limitation,
and no full-release consumer/proof/admission. Record512 remains the only evidence
path; old source/test/evidence are read-only. No further source authoring, real
checker execution, catalog admission or next ticket is authorized. Stop reviewer.


## Lint stop — exact mechanical source continuation

Hermes message 99905 records scoped Ruff exit 1: F402 for the decoder's local
field loop variable shadowing dataclasses.field, and F841 for the unused result
assignment in the refused test helper. Control/whitespace did not execute. No
record/integration occurred. Preserve the accepted 22-case runtime result.

Authorize the same sole GPT-6 Sol High actor for exactly these two mechanical
changes in the existing two writable paths: rename the decoder's loop variable
and its references; remove only the unused result assignment, retaining the call
to original. No behavior, assertions or other source changes. No tests, lint,
imports/probes, data, records, Git or integration by the senior. Return new hashes
and stop. Hermes is stopped until reviewer verifies the exact diff and resumes it
at Ruff; do not repeat setup or the passing targeted tests.


## Mechanical correction accepted — final Hermes resume

The reviewer compared both files against the frozen pre-lint copies. The only
changes rename field to schema_field in the decoder loop and remove result = from
the refused helper's original call. They preserve behavior and all assertions;
retain the accepted 22-case targeted result without retesting. Final hashes:

| Path | SHA-256 | Lines |
| --- | --- | ---: |
| scripts/research/check_cex002_nautilus_consumer.py | 6ac5fd0dbf4c676ccaf87fc288d68c3725a170a1de5aefe9babe497b2fb9584e | 795 |
| tests/test_cex002_nautilus_consumer.py | 37363e911a82cb2c7394cbb806f2acbe9c8b35a148f16f12c69ca8ebcd54802e | 442 |

Senior is stopped. Hermes now authenticates these final hashes and resumes only
scoped Ruff, control, whitespace, then Record512 and the original exact three-path
commit/push guards. Record both failed checks and their disposition, plus the
accepted senior 22-pass run attributed accurately; no other tests or setup reruns.
First nonzero/denial stops without source repair/retry. The mechanical edits do
not reopen runtime behavior. No full-data proof, admission or next ticket. Stop
for reviewer inspection after publication.


## Integration accepted — reviewer checkpoint

Accept Hermes integration b186b3a250ee147bb8d55311090bfb232f90e3ab and Record512. Native messages 99915–99926
confirm final scoped Ruff, repository control, unstaged/staged whitespace all
passed, exact three-path publication, normal push and empty index. The reviewer
independently verified that commit's complete path set and both committed SHA-256
values against the final frozen drop. HEAD equals origin/main; unrelated dirty
work remains untouched. The accepted senior 22-case targeted result is retained
with its attribution and the mechanical no-behavior-change qualification. Record512
honestly preserves both initial failures and setup sanity limitation.

This accepts checker implementation/integration only. No full-release consumer
execution/proof, catalog admission, replay, remaining economic evidence or final
ticket acceptance occurred. The non-consumable prepared candidate and accepted
products remain unchanged. Hermes and the senior have finished this assignment.
Next actor is the reviewer to bound the real consumer check, including measured
throughput/capacity before committing to the 1,165,116,869-row traversal. No new
execution is authorized by this checkpoint; CEX-002 IN_PROGRESS, next ticket NONE.
