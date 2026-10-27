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


## Final source acceptance and complete Hermes workflow

Reviewer accepts the bounded source drop after full source inspection and the senior's
second, explicitly authorized focused command above: exit0, 25 passed in3.77seconds.
The earlier exit1/21passed/2failed remains evidence; no real run has occurred.
Frozen source: scripts/research/reconcile_cex002_admitted_release.py,596lines,
SHA256 857aec234bc5ebb5905a32d6383fb7f7d59cbf8dbf6da435c5042fd1b095041b.
Frozen tests: tests/test_cex002_admitted_release_reconciliation.py,423lines,
SHA256 e0f3d7e8d5b5e66a2daa431f4fd3d7b6c4b886d1c8cbb4fb18d01df8f92ec768.
The successful tiny real-Parquet/catalog case traps logical row readers. Fixed
accepted anchors remain immutable. Senior source work is stopped; Hermes now owns
the following ordered integration, one bounded execution and evidence publication.
Do not repeat the already passed focused pytest or old consumer/admission/replay.

### Integration, stop on first failure

Require HEAD==origin/main, empty index and both exact frozen worktree hashes; preserve
all unrelated dirty paths and accepted original runtime/checker/candidate/proof/publication.
Run exactly these remaining integration checks in order, stopping on the first failure:

```bash
.venv/bin/python -m ruff check scripts/research/reconcile_cex002_admitted_release.py tests/test_cex002_admitted_release_reconciliation.py
python3 scripts/check_repo_control.py
git diff --check
```

Write research/sprint_004/523_CEX002_KNOWN_RELEASE_RECONCILIATION_INTEGRATION_RECORD.md
with actual commands/statuses, frozen hashes, senior test attribution and first failure
history. Stage exactly the new script, new test and Record523 (three paths); guard exact
staged set, cached whitespace, normal commit/push, HEAD==origin/main and empty index.
No source/test edits, test design, auto-fixes or widened integration. A failure stops
for reviewer; do not run the real reconciliation until successful integration.

### One bounded real reconciliation, actively monitored to terminal

After successful integration, execute the following capture once from the repository
using native terminal background=true,notify_on_complete=true,pty=false. The project
.venv, PYTHONPATH=src and exact command/source pin are mandatory. Do not use the old
isolated consumer environment. No installation, cleanup, source patch, duplicate run,
old generic publish/read CLI, full proof rerun, logical-row transport or data writes.
The command owns its rollback-only transaction. Internal/external deadline1800seconds;
any failure/timeout stops without retry. Native background-launch exit0 is not PASS.

```bash
cd /home/lars/Crypto_Multifactor_Bot
set -euo pipefail
record=research/sprint_004/524_CEX002_KNOWN_RELEASE_REPLAY_READBACK_RECORD.md
if [ -e "$record" ] || [ -L "$record" ]; then echo 'Record524 already exists; stop'; exit 1; fi
set -o noclobber
exec 3> "$record"
set +o noclobber
exec 4>> /dev/fd/3
exec 3>&-
printf '# CEX-002 known-release replay/readback execution record\n\nLaunch UTC: ' >&4
date -u +'%Y-%m-%dT%H:%M:%SZ' >&4
printf 'Execution HEAD: ' >&4
git rev-parse HEAD >&4
printf '\n## Raw execution output\n\n```jsonl\n' >&4
set +e
PYTHONPATH=src /usr/bin/timeout --signal=TERM --kill-after=60s 1800s /home/lars/Crypto_Multifactor_Bot/.venv/bin/python -u scripts/research/reconcile_cex002_admitted_release.py --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --source-sha 857aec234bc5ebb5905a32d6383fb7f7d59cbf8dbf6da435c5042fd1b095041b 2>&1 | tee -a /dev/fd/4
pipeline_status=("${PIPESTATUS[@]}")
audit_status=${pipeline_status[0]}
capture_status=${pipeline_status[1]}
printf '```\n\nAudit/deadline exit status: %s\nOutput capture exit status: %s\n' "$audit_status" "$capture_status" >&4 || exit 1
exec 4>&-
if [ "$capture_status" -ne 0 ]; then exit "$capture_status"; fi
exit "$audit_status"
```

Keep the held append FD and tee -a: never truncate/rewrite captured bytes. Poll the
same native session once to confirm startup, then supervise that same session to
terminal (reviewer reads progress too). Record counters are CUMULATIVE hash operations
and bytes across safety passes; they are not unique-file percentages. Expected unique
closure423446files /38950242846bytes. There is no new logical-row/Nautilus run.

### Terminal evidence and publication

On terminal status, inspect the emitted JSON and exact exit status; no extra dataset
scan, verifier, catalog mutation or acceptance rerun. PASS requires the exact scope
accepted_proof_unchanged_bytes_and_catalog, all fixed pins, complete unique counts,
accepted all-column catalog anchors and unchanged quarantine, reused accepted value
proof=true, fresh physical/footer authentication=true, new logical/Nautilus run=false.
This proves only ADR0040's known admitted release checkpoint; the old replay failure
remains failed. On failure preserve raw output/status and stop without retry.

Authenticate the raw captured prefix before appending a concise actual-run narrative:
Hermes model/provenance, exact command, integration HEAD, launch/finish times, terminal
status, scope, counts, pins/resources/anchors and limitations. Preserve its bytes and
verify the prefix digest after append and from committed content. Publish only
Record524 with exact-one-path staging guard, cached whitespace and normal commit/push;
verify HEAD==origin/main and empty index, then STOP for reviewer. Record a failed
terminal result truthfully too; never label a launch or interrupted run PASS.
No extra review handoff between these successful steps. Reviewer keeps active track
through terminal result and evidence publication. Full-ticket economics/final suite
and acceptance remain pending; CEX-002 IN_PROGRESS, next ticket/authorization NONE.


## Reviewer terminal acceptance — 2026-10-27

Accept source integration9b24ceac34a40f2ee0aaf20d774a6e344b1ce1c1 /Record523
with the explicit narrative errata in Record524. The committed three-path set and
both frozen source hashes match the accepted drop. Senior focused feedback25passed
in3.77seconds and Hermes scoped Ruff/control/whitespace all passed. No test was
repeated to recover executor availability. Historical21passed/2failed stays recorded.

Accept the ONE real known-release reconciliation under ADR0040: launch2026-10-26
23:47:45UTC, reported elapsed773.097seconds (12m53s), native process uptime774seconds,
execution exit0 and output-capture exit0. Jobproc_8e5ec0014d2f is terminal/exited;
Hermes is stopped for reviewer. There is no outstanding run or retry assignment.
The1800second deadline was not reached. The exact project-environment CLI is in
Record524; native capture used condensed shell chaining rather than the review block
verbatim, with both actual terminal statuses0 and the complete output preserved.

Final evidence publication: 2f9f14485127f72ca0003fcc2331a2dbdb406dde, following
first correctioncf449175d045cb6ffc3cd177802cd7e1f6a5d32c and
initial Record524 publication9d6ba2c50c9af18dddb5ddd06591fccb4777eeee. Final record:
research/sprint_004/524_CEX002_KNOWN_RELEASE_REPLAY_READBACK_RECORD.md,
39374bytes, SHA256dc3eec2f927cc9353dd9a5dc56e85abecc82254bcec4f3ddb2a9dfb79b5fcbd0.
The original35462byte captured prefix retains SHA256
3c8a5c67e5cc3be667864c60cbcc41868e69a99740464563c56c2b70f525d370 in both worktree
and committed content. Reviewer independently inspected the raw final JSON, terminal
status, source hashes, exact integration/publication paths and empty staging index;
HEAD==origin/main at2f9f144 before this reviewer-only governance publication.

Confirmed scope: accepted_proof_unchanged_bytes_and_catalog. All423446 files were
freshly authenticated (178947 tables,244499 metadata references;38950242846 unique
physical bytes),11 datasets,10 dataset dependency edges and0 raw edges. The historical
1165116869-row full consumer/value evidence was reused; no new logical-row decoding
or Nautilus run occurred. Candidate8b46beb… /publication5ea2227… /proof3be8597… /
checkerac83cc2… and original source commit1f5629b… match their fixed authorities.
All four complete catalog snapshots match the accepted anchors above, and five-row
quarantine digestb4334b2… is unchanged. Identical replay rolled back; independent
read-only catalog reconciliation passed. No release/catalog-row changes or repair.
Observed free198410391552bytes preserves the29690701415byte operating reserve;
reserved metadata3958751427 remains within4985471619bytes. No cleanup occurred.

Executor attribution/record errata: the old LongCat free endpoint returnedHTTP404
before any integration or real run. A fresh Hermes session20261026_163106_0df3aa used
Laguna S2.1 for the successful integration checks, then hit upstreamHTTP429 capacity.
Step3.7Flash continued that SAME saved session, integrated source and executed the
real run. Record523 was not corrected before integration; its inaccurate model
history and Record524's initial false session-history sentence are corrected by the
appended Record524 correction. The initial working-tree diff labeled INDEX_EMPTY=3
was the wrong query; the actual staged index was empty, subsequently checked with
git diff --cached --name-only. The integration printed the exact expected staged set
rather than asserting its equality automatically; reviewer independently verified
that committed set. The terminal record publication used an exact-one-path assertion.
These documentary/control-query limitations do not invalidate the observed source,
actual executed checks or complete no-change real reconciliation. Do not rerun them.
One record-only correction command failed shell parsing (exit2) before any append;
the corrected append then passed. A late queued record-only instruction added the
same correction a second time; no audit was repeated. Its final staged-index query
misspelled --name-only as --name-name and printed Git usage; reviewer independently
confirmed the actual index empty and HEAD==origin/main. All publication commits touch
only Record524. The completed executor was closed with no child job to prevent further
queued work. Original raw bytes were never changed.

This satisfies the existing known admitted release replay/readback requirement under
ADR0040. Preserve Record521's original capacity-failed replay as FAILED, the accepted
initial admission and Record518's full consumer PASS. This is not a successful rerun
of the old generic CLI, an initial-admission shortcut or full-ticket acceptance.
Remaining CEX-002 work: independent economic examples/reconciliation evidence, the
consolidated final release/coverage report and original full acceptance commands.
No new source, data run, old verifier, cleanup or next ticket is authorized here.
Next required actor is the Lead reviewer for that fixed closeout evidence assignment;
CEX-002 remains IN_PROGRESS and next ticket/authorization remain NONE.
