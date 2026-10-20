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

Reviewer continuation before the targeted slot: the complete strict proof has one
12-key entry per file with three digests and path/count/time fields; 423,446 entries
must not be assumed to fit the former 256 MiB read ceiling. ADR-0038 now explicitly
authorizes PROOF_MAX_BYTES=512 MiB as a finite metadata read bound, with no proof-schema
change or storage allocation increase. In the synthetic budget regression calculate
representative full-proof encoded bytes at this count and require them to fit that
bound; reserve the full 512 MiB ceiling in the combined-capacity scenario. All actual
proof bytes still debit the fixed metadata remainder. Other resource pins and the
SQLite reservation formula/multiplier remain unchanged.

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

## Terminal Record 506 acceptance

Accept Record 506's terminal failure evidence at publication
362c167ecf91b00145b6d06e73e353604cd816a2, following initial record publication
2e5d5a6a3fbae916d98c69d05db5a039bfa33b42. The correction preserves the existing
bundle object and distinguishes the fixed release-wide allocation from an unmeasured
component subtotal. Exact producer output/process/source commit agree with native
tool evidence. Full before/after catalog digests match; no CEX rows were admitted.
Post-failure free space is 76,807,471,104 bytes. Both commits contain only Record 506,
normal pushes completed, and the index is empty. Hermes has finished and stopped.
No producer retry, cleanup, proof or catalog admission follows from this acceptance.

## Final source acceptance and measured synthetic budget

The single targeted command returned exit 0, 63 passing progress marks, and printed
the computed synthetic budget below. The reviewer inspected the complete production
and test diffs and independently verified:

| Path | SHA-256 | Lines |
|---|---|---:|
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | fed0d0ef49eb3704be577a378dfd12eb7e6876fc41fbfe9d6507e7ef5b83fe00 | 2237 |
| tests/catalog/test_cex002_reference_release.py | 293f45157c94e9978e18aa0f6720cc68ab8c230c19524abe0cf9140a87acfc8a | 1261 |

The three unchanged hashes are ingest source
1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b,
CLI cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9,
and ingest test 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0.

| Charged class | Synthetic bytes |
|---|---:|
| Eleven serialized manifests | 252,802,987 |
| Prepared descriptor ceiling | 8,388,608 |
| Publication descriptor ceiling | 8,388,608 |
| Full proof read ceiling reserved | 536,870,912 |
| Leftover-file allowance | 13,232,150 |
| Unchanged 12x SQLite reservation | 3,655,335,936 |
| Total | 4,475,019,201 |
| Fixed remainder | 4,985,471,619 |
| Headroom | 510,452,418 |

The representative complete proof encodes to 281,881,986 bytes, exceeding the old
256 MiB ceiling and fitting the new finite 512 MiB ceiling. All 423,446 file references,
178,947 tables and 244,499 metadata files are represented across eleven manifests,
with long paths, dictionary/decimal/list contracts and metadata partitions. Registry
and manifest read bounds also pass. This is a conservative synthetic scenario, not a
measurement or acceptance of the eventual real candidate; its real guard remains final.

Accept the source for integration under ADR-0038. Registry contracts are canonical,
bounded, hash-bound and required at every manifest/footer path. Field order/types/
nullability and complete proof tokens remain enforced. The SQLite formula, object cap,
metadata allocation and reserve are unchanged; resource errors now expose exact charged
classes. The source actor has stopped. No reviewer test or data operation occurred.

## One-way Hermes integration, exact orphan disposal and one preparation

Continue the owner-approved direct native Hermes route using the existing free Nous
session and normal interactive approvals. This section authorizes the following complete
ordered workflow. Preserve unrelated changes. Stop at first nonzero, denial, identity
mismatch or unexpected inventory, without repair/retry. Do not author source/tests,
helpers, architecture or implementation substitutes; never read archive. GPT-6.1 remains
reviewer. The named source correction is accepted; final release acceptance is pending.

1. Confirm HEAD==origin/main and empty index. Verify all five frozen hashes above and
   the three unchanged paths. The owned bundle root now legitimately exists: do not
   apply the earlier absent-root requirement. No producer is assigned before step 4.
   Run exactly once in order (one set -e terminal group is permitted):

   ```bash
   .venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/ruff check src/cryptofactors/catalog/dataset/cex002_reference_release.py tests/catalog/test_cex002_reference_release.py
   .venv/bin/python scripts/check_repo_control.py
   ```

2. If all pass, write only
   research/sprint_004/508_CEX002_SHARED_SCHEMA_INTEGRATION_RECORD.md with actual
   model, commands/results, five hashes and the developer's separate 63-case/synthetic
   result. Recheck hashes; stage exactly the TWO changed catalog paths above plus Record
   508, inspect names and git diff --cached --check. Commit as
   CEX-002: share schema contracts within the fixed release metadata budget
   and push normally. Verify HEAD==origin/main and empty index; retain the full new
   source integration commit and verify its five committed blobs. No amend/reset/force
   push or unrelated staging. The terminal record will pin that resulting full commit.

3. Capture BOTH complete ordered read-only catalog query results from Review 496,
   full deterministic JSON digests and all ID/status pairs, before any disposal/launch.
   Require zero CEX reference rows and the unchanged five REJECTED/REGISTERED rows.
   Inspect ONLY the owned bundle-root filename inventory. Require exactly one regular
   non-symlink file, at the exact failed object path recorded above, with no symlinked
   path components or other files, prepared descriptors, manifests, proof/publication
   files or abandoned stages. Empty directories are allowed. The prior native process
   proc_311fa1978b3f is already terminal exit 1; do not launch a second old-code run.

   Authenticate that sole object's complete SHA-256 equals
   8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f
   and its size is exactly 13,232,150 bytes. Record path/SHA/size and the no-candidate/
   no-catalog-reference evidence. Then unlink ONLY that exact unreferenced, regenerable
   failed-attempt file once. This narrow disposal is explicitly authorized to prevent
   the new code identity's bundle object plus the obsolete object exceeding the fixed
   object cap. It removes no accepted product, sealed candidate or unique user input.
   Do not remove its directories, any other file, accepted older kline artifact or
   unrelated work. Confirm no owned file remains. An unexpected state or action denial
   stops without cleanup substitution/retry; preserve evidence and report the reason.

4. Capture free bytes and retain the full catalog baseline BEFORE launch. Invoke once,
   replacing SOURCE_COMMIT only with step 2's new literal full source integration hash:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit SOURCE_COMMIT
   ```

   Use native background=true and notify_on_complete=true and track that SAME process
   to terminal. New writes stay under data/.cex002_harmonic_bundle; accepted inputs,
   all allocations and reserves remain fixed. No duplicate launch/private diagnostic,
   producer replay, proof generation, consumer run or catalog admission.

5. On success apply Review 496 step 4's descriptor/eleven named manifests/bundle footer/
   owned-inventory inspection, including transform v2, shared registries, all eleven IDs,
   ten dependency edges, file/table/main/gap counts, bundle SHA/rows/bytes/schema,
   separate retained-kline audit and liquidation gap/comparison metadata. Confirm the
   single bundle object and consumable=false, with no proof/publication or abandoned
   stage files. Report actual manifest/descriptor bytes and the real SQLite reservation
   from sealed metadata or an inline invocation of existing _sqlite_reservation on those
   loaded manifests only; do not authenticate accepted tables again merely to total a
   budget. No new checker/helper file. On failure retain exact rich output/charged
   subtotals and preserve created files; no further product inspection or repair.

   In either terminal case repeat only the same two read-only catalog queries and free
   space observation; require the complete ordered-row digests/ID statuses unchanged.
   Terminal evidence publication remains allowed after a producer failure.

6. Publish only research/sprint_004/509_CEX002_SHARED_SCHEMA_BUNDLE_PREPARATION_RECORD.md
   with actual literal command/source commit/model/process/exit/output, frozen hashes,
   exact orphan-disposal evidence, correctly timed full catalog baselines/resources and
   candidate facts or blocker. Distinguish synthetic estimates from measured output.
   Stage that record alone with empty-index/staged-name/staged-whitespace checks;
   commit/push normally, verify HEAD==origin/main and empty index, then stop for reviewer
   inspection. Do not stage reviewer governance, source, data or unrelated files here.
   Record/Git failure stops publication without repair/retry.

No next ticket or final Gate acceptance is authorized. This ordered continuation alone
supersedes the preceding source-only ban on cleanup and another real preparation.

## Integration acceptance and bounds-marker continuation

Accept integration 1f5629badfa0e8af6338fbeb019a5f7e60b6a324 and Record 508. The
reviewer independently matched all five committed hashes and the exact three-path
commit. Hermes's grouped validation passed 162 cases, Ruff and repository control,
with the same full-count synthetic result. Preserve these checks; do not rerun them.
Record 508's progress-line split is inaccurate; the native output totals 162 and exit
0. That transcription does not change the accepted validation result.

Hermes then found two owned files rather than this review's expected one and stopped
without unlinking or launching a producer. It additionally read/hash/stat inspected
the unexpected marker after inventory discovery; this exceeded the literal immediate
stop instruction, but was read-only and changed no data. Preserve that disclosure in
Record 509 rather than silently claiming perfect stop compliance.

The reviewer confirms that _guard_resources intentionally calls _write_bounds for
metadata_remainder_exceeded. The latter writes a non-consumable BOUNDS_DOCUMENT under
.prepared. The reviewer's one-file precondition overlooked this existing failure path;
there is no new source defect and no completed candidate at this point. The marker is:

- data/.cex002_harmonic_bundle/.prepared/a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a.json
- SHA-256 a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a; 305 bytes.
- document_type=cex002_harmonic_bundle_bounds_block, schema_version=1,
  consumable=false, blocker=metadata_remainder_exceeded, detail stage=prepare and
  the exact Record-506 values 7,450,831,574 / 4,985,471,619 / 5,556,368,003.

Authorize the existing Hermes session to resume only the remaining workflow from
step 3, using source commit 1f5629badfa0e8af6338fbeb019a5f7e60b6a324. No source,
tests, integration, validation or new helper is assigned. Refresh the same two complete
read-only catalog snapshots and free space before disposal/launch; require their frozen
zero/five rows and digests. Recheck five unchanged source hashes, empty index and
HEAD==origin/main; reviewer governance may have advanced HEAD past that source commit.

Replace the one-file precondition with EXACTLY the two regular, non-symlink files
enumerated here and in step 3: the old 13,232,150-byte object and this 305-byte bounds
marker. Verify both full hashes/sizes and marker contents before action, no symlinked
components, no additional files or live producer. Keep the marker unchanged. Unlink
ONLY the originally authorized old object, after the original no-candidate/no-catalog
reference guards. Verify the sole remaining owned file is the unchanged marker.
No directory, marker, accepted product or other file may be removed or moved.

Then resume steps 4–6 once: capture full pre-launch baseline/free bytes, launch the
exact prepare command using the full source commit above with native background/notify,
monitor the SAME process, perform the original success-only candidate inspection and
post-catalog comparison, and publish terminal Record 509 only. On success allow exactly
one newly sealed candidate alongside the preserved bounds marker; require each document
type and emitted candidate SHA to be unambiguous. The marker's 305 bytes remain charged
as existing descriptor metadata under the unchanged resource guard. Preserve its hash
and explicitly distinguish it from the new candidate in Record 509.

Stop again on first unexpected state, denial or nonzero without inspection/repair/retry.
Producer failure still permits terminal disclosure/Record-509-only publication. Normal
approvals, immutable accepted data, budgets and absence of catalog admission/proof/
consumer work persist. This continuation corrects governance only; no new producer
has yet run from source 1f5629b.

## Capacity preflight stop — 2026-10-19

The refreshed native preflight (message 99228) reports 20,142,739,456 available
bytes, below the unchanged operating reserve of 29,690,701,415 by 9,547,961,959
bytes even before incoming data and metadata reservations. The five source hashes,
empty index, synchronized 6537b07 HEAD and both frozen catalog digests still match.
This is an environmental capacity blocker, not a new source or schema failure.

The reviewer sent an immediate native steer before any further logged action:
stop before object disposal or producer launch; preserve both owned files. This
section supersedes the disposal/launch continuation while capacity is insufficient.
Hermes publishes only terminal Record 509, disclosing actual actions and capacity,
then stops. If any action was already in flight, report it exactly; do not claim an
unobserved stop. No retry, source change, accepted-data deletion, proof, admission,
or next ticket is authorized. Preserve the passed 162 cases and integration.

The real preparation remains unexecuted from source 1f5629b. Restore sufficient
filesystem capacity before any later bounded execution authorization. The reserve
alone is a lower bound; the existing guard also charges incoming bytes and actual
release metadata. The 4,475,019,201-byte synthetic charge is not a real candidate
measurement and does not establish a launch floor.

A conservative later prelaunch floor is 34,724,877,040 bytes: unchanged reserve
29,690,701,415 + full metadata remainder 4,985,471,619 + twice the bundle cap
24,352,003. Relative to message 99228 this requires 14,582,137,584 additional
available bytes. This derived capacity check changes no allocation or guard and
does not authorize cleanup or a relaunch; the real guard remains authoritative.

## Terminal capacity record accepted

Accept Record 509 at 17122ed7040d56a753c1a3792e2bd90624e23d7a as the stopped
preflight result. Reviewer inspection confirms its exact one-record commit, native
successful push, synchronized HEAD/origin and empty index. Native messages 99228
and 99232 authenticate the unchanged catalog/source identities and both preserved
owned files. No disposal, new producer or new candidate occurred. The reviewer
capacity steer ended the pending workflow; this is not a producer exit failure.

Record 509's displayed old-object path has an extra `e` in its basename. Its
64-character SHA and the exact earlier Review-507/native inventory path are
authoritative; the typo authorizes no alternate path. No repeat record cycle or
test rerun is needed to resolve that transcription.

Hermes is finished and no source actor is assigned. Next actor is the reviewer for
the capacity-restoration decision. CEX-002 remains IN_PROGRESS, with an explicit
capacity blocker and next ticket NONE. Preserve all data and accepted checks; no
cleanup, relaunch, proof, catalog admission or next-ticket work is authorized.

## Capacity restored — bounded preparation resume

The owner reports deleting files. Reviewer read-only df now observes 148,586,504,192
available bytes, above the unchanged conservative 34,724,877,040-byte prelaunch
floor. HEAD==origin/main==dfdf5f9872a277ef7de8f2eda9b0ae5461d81e42 and the index
is empty. This resolves the environmental stop only; accepted input existence and
identities must still be authenticated by the existing producer.

Authorize the same native free Nous Hermes session to resume the remaining workflow
once, without tests, reintegration or source changes. This section supersedes the
capacity-stop ban solely for the following bounded execution. Preserve Record 509.

1. Refresh HEAD/origin equality, empty index, the five frozen hashes, BOTH complete
   read-only catalog snapshots/digests/status pairs, and free bytes. Require the
   unchanged zero/five catalog rows and free bytes >=34,724,877,040 before disposal
   and immediately before launch. Reviewer governance may have advanced HEAD.
2. Apply the exact TWO-file authentication and disposal guards in the bounds-marker
   continuation: authenticate the old 13,232,150-byte object and 305-byte marker,
   no symlinks or extra files/candidates/stages and no live producer. Unlink only
   the old object whose full SHA is
   8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f.
   Retain the exact a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a
   bounds marker unchanged. Do not delete directories, accepted data or other files.
3. Execute the original steps 4–5 once, using the exact full source commit
   1f5629badfa0e8af6338fbeb019a5f7e60b6a324. Use native background/notify and
   monitor that SAME process through terminal. On success inspect the candidate,
   eleven manifests, bundle footer, real resource totals and owned inventory as
   assigned above; distinguish the preserved bounds marker from the candidate.
   In either terminal case repeat both full read-only catalog snapshots and free
   bytes, require unchanged catalog digests, and preserve exact output/exit status.
4. Publish ONLY
   research/sprint_004/510_CEX002_SHARED_SCHEMA_BUNDLE_PREPARATION_RESUME_RECORD.md
   with the complete original terminal evidence, capacity restoration, actual
   disposal and measured result/blocker. Never overwrite Record 509. Empty index,
   exact one-path staged-name/whitespace checks, normal commit/push, synchronized
   HEAD/origin and empty index, then stop for reviewer inspection.

Normal approvals and first-nonzero/denial/unexpected-state stops persist, with terminal
record publication allowed after producer failure. No retry, arbitrary cleanup,
accepted-data change, proof/consumer execution, catalog admission, new source actor,
or next ticket is authorized. The real resource guard and all allocations remain fixed.
Reviewer publication remains exactly this Review 507, CURRENT_TASK and CEX-002 ticket.

## Successful preparation and bounded inspection correction

The one resumed producer proc_2dad8d51733f / PID 1918894 exited 0, reported at
845 seconds, and emitted candidate
8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.
The reviewer independently matched its 11,020-byte descriptor and all eleven
manifest physical hashes/byte pins (228,098,515 bytes total), and inspected their
metadata counts. Hermes authenticated the new 13,232,150-byte object
32029cf9cd182839719574f3963e2faa89935c682ed861712be5ef07c23a381c,
its 178,946-row footer, preserved marker and unchanged post-catalog digests.
Post-run free space is 147,669,061,632 bytes. No producer retry is needed.

The sole measured _sqlite_reservation result is 3,458,088,960 bytes. Together with
manifest bytes, descriptor and preserved 305-byte marker, preparation charges
3,686,198,800. Adding a full 536,870,912-byte proof allowance and 8,388,608-byte
publication ceiling gives 4,231,458,320, below the fixed remainder by 754,013,299.
Those future allowances are not a measured consumer proof/publication.

Hermes's read-only inspection 99860 used absent dataclass row_count/byte_size
attributes and printed None; their actual locations are statistics.row_count and
statistics.byte_size. Pending inspection 99862 likewise uses wrong JSON key paths.
It must not treat zero/None outputs as product facts or substitute them for counts.
These are inspector errors, not changes to the accepted source or real candidate.

Authorize exactly one corrected metadata-only inspection after that pending call,
using the actual paths confirmed by reviewer artifact inspection:

- File kind and schema_ref live under file.partition.
- Schema registry lives under manifest.quality_summary.schema_registry, with
  version/contracts. Metadata files have zero rows and no schema_ref.
- Liquidation counts/comparison live under manifest.quality_summary: daily quality
  gaps 4,626, authority gaps 202, comparison entries 18.
- Dependency entries use id/kind/role; the bundle has the ten constituent edges.
- Raw manifest row_count/byte_size and file.rows are top-level wire fields.

Complete the already assigned table/metadata/count/registry checks in that one pass:
178,947 table files +244,499 metadata files =423,446. Record the earlier inspector
limitations honestly in Record 510, then its exact one-record commit/push and stop.
Do not repeat the producer, SQLite calculation, completed hashes/catalog snapshots
or tests. No new helper/source/data repair, proof, admission or next ticket is assigned.

## Preparation accepted — consumer check remains pending

Accept Record 510 at 16765eedc87eba67bbe18cda90afaf5301d6b28d and the successful
non-consumable candidate 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.
Reviewer commit inspection confirms exactly the one assigned record path; native
publication succeeded with synchronized HEAD/origin and an empty index.

The corrected native inspection 99865 reconciles 178,947 table files and 244,499
metadata files, totaling 423,446, with 1,165,116,869 physical table rows. The bundle's
178,946 rows describe the ten constituents' table files; its own one table accounts
for the additional table-file count. All eleven registries are version 1 under
transform version 2. The ten dependency IDs/roles and separate liquidation counts
4,626 /202 /18 match. No source, test, producer, SQLite calculation or catalog check
was repeated to correct the earlier inspector field-path errors.

Reviewer artifact inspection independently matches the descriptor and all eleven
manifest physical byte/hash pins. It also finds no missing schema references,
unused contracts, inline repeated contracts or invalid metadata entries. In Record
510, schema_ref applies to table partitions only; metadata has zero rows and no
schema_ref. Its abbreviated inspector disclosure covers both the absent dataclass
attribute probe and the wrong JSON nesting probe recorded above. The immutable
liquidation comparison's pending_reviewer string is retained provenance, not a
reversal of the already accepted comparison evidence.

Record 510's 148,463,267,840-byte observation is the refreshed preflight. The final
immediate-prelaunch observation was 148,369,633,280 (native 99831), and post-terminal
was 147,669,061,632 (99855). Both complete catalog digests are unchanged. The real
preparation charge and future allowance calculation above fit the unchanged budget;
no reserve, allocation or accepted input was changed.

Hermes is finished; the source actor remains stopped. Next actor is the reviewer to
bound the existing clean NautilusTrader consumer check for this exact candidate.
The strict full-release proof, catalog admission, release replay, remaining economic
evidence and original final acceptance commands are still pending. No checker source
actor, consumer run, proof generation, admission, producer retry or next ticket is
authorized by this acceptance. CEX-002 and Gates 3–5 remain IN_PROGRESS.
