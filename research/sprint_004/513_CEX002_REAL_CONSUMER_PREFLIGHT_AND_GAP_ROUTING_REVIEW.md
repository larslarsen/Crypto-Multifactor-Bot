# CEX-002 Review 513 — Real consumer preflight and bar-gap routing

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Source actor: Sr Dev — Codex Sol, GPT-6 Sol High (sole bounded senior)
Architecture: ADR-0039 unchanged

## Accepted starting point and actual-manifest finding

Review511 accepts integration b186b3a250ee147bb8d55311090bfb232f90e3ab,
Record512, the senior's 22 targeted cases, final scoped Ruff/control/whitespace.
Preserve those results and all accepted data. Candidate remains
8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.

Before real execution the reviewer inspected the eleven pinned JSON manifests.
The bar manifest has 22,633 main tables /16,033,469 rows with component="", and
one 154-row gap table with component="quality_gap". BOTH have role="partition".
Current native-Bar selection uses dataset type and role only, so the real gap
schema would be rejected for lacking OHLC. The original tiny full-proof fixture
contains no bar-gap table and omitted the real component field. No consumer
execution has occurred and no data correction is warranted.

Actual gap reference:
data/.cex002_bar_1h/.quality-gaps/467853875cfb1570dcb6de953f4af54af03cab4adf6c9fd7a39143a83c4cc9e4.parquet
154 rows; 5,039 bytes; SHA256 467853875cfb1570dcb6de953f4af54af03cab4adf6c9fd7a39143a83c4cc9e4.

## Exactly two writable senior paths and fixed decision

- scripts/research/check_cex002_nautilus_consumer.py
- tests/test_cex002_nautilus_consumer.py

Select the existing GPT-6 Sol High actor for this small reviewer-designed guard
and representative fixture correction, using its accepted codec/proof context.
GPT-6.1 remains stronger reviewer; no second senior or new architecture.

For TABLE components in the bar dataset, require the accepted role="partition"
and an explicit component of either "" or "quality_gap". Only component=""
gets mandatory native Bar projection; a quality_gap table gets complete custom
row transport and the same proof/digest/schema authentication. Reject unknown or
missing component tags and unknown roles; malformed primary bar schema must still
fail and cannot opt out by dropping columns. Do not infer type from field shape.

Update tiny private fixtures to include actual component tags. Add a real gap
schema/table within the eleven-dataset end-to-end test, proving its exact source
and readback digests and inclusion through the strict existing verifier, while
main bars still receive native write/readback. Add malformed primary schema and
unknown/missing tag/role refusal cases. All existing tests remain; no production
candidate overrides, codec/proof/resource/schema changes or data editing.

The corrective senior-test exception authorizes exactly ONE execution after edits:

```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
```

Stop at first nonzero and return exact full command/output/status without repair
or retry. If all pass, return frozen two-path hashes/line counts for source review.
No other tests, lint, probes/import commands, install, real data, records, Git,
commit, push or integration. The existing pinned isolated environment is reused.
Hermes is not yet authorized to validate/integrate or run real data. Reviewer will
separately enumerate that workflow after source acceptance. No full-release proof,
admission, economic promotion, other ticket or automatic cleanup.

## Capacity/scale observation (reviewer metadata only)

At this continuation, df reports 298,949,865,472 SSD bytes available and
30,694,170,624 /tmp bytes. Fixed operating reserve remains 29,690,701,415.
Physical release rows remain 1,165,116,869. Cost calibration alone has 939,131,092
rows, including 882,076,090 retained ticker rows. Full real runtime cannot be
claimed from fixture timings; bounded actual-component measurements are needed.
No throughput result or consumer PASS exists yet.

## Reviewer governance publication scope

Exactly this Review513, docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md.
No developer source/test/evidence/data integration by the reviewer.


## Corrected source accepted; Hermes integration and bounded real measurement

The senior executed exactly the assigned targeted command, exit0: 27 passed in
2.47s. The reviewer inspected the complete two-path diff and independently matched
these frozen hashes. The strict eleven-dataset fixture now includes a realistic
bar-gap schema and checks its full component against the existing strict verifier;
five refusal cases protect malformed primary schema and missing/unknown tags/roles.
The source actor is stopped. Accept for Hermes integration, not real-release PASS.

| Path | SHA256 | Lines |
| --- | --- | ---: |
| scripts/research/check_cex002_nautilus_consumer.py | ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117 | 798 |
| tests/test_cex002_nautilus_consumer.py | c4e051a1b9e0f9ae9df983f4319c2f4370cbe108b2d88b2632af8768d4465ff5 | 521 |

Use a fresh native Hermes session, meituan/longcat-2.5-preview:free via Nous, normal
approvals/rules, to avoid prior accumulated-context latency. This is Jr Dev's
existing execution/integration role, not another source author. Existing isolated
/tmp/cex002_nautilus_review511_env is accepted; do not install or repeat setup/tests.

### A — ordered integration (Hermes only)

1. Require HEAD==origin/main, empty index, and the frozen hashes above; preserve
   every unrelated dirty path. Run once in order (set-e grouping permitted):

```
.venv/bin/python -m ruff check scripts/research/check_cex002_nautilus_consumer.py tests/test_cex002_nautilus_consumer.py
python3 scripts/check_repo_control.py
git diff --check
```

2. Stop first nonzero/denial with exact output, no source repair/retry. Only all-pass:
   write research/sprint_004/514_CEX002_BAR_GAP_ROUTING_INTEGRATION_RECORD.md with
   actual commands/results, source hashes, 27-pass senior targeted attribution and
   scope. Stage EXACTLY the two frozen source/test files plus Record514, require
   staged-name equality, git diff --cached --check, normal commit/push, then require
   HEAD==origin/main and empty index. Reauthenticate committed source hashes. Source
   edits, other records/Git paths and test repeats are forbidden.

### B — ONE real measurement after A succeeds (Hermes only)

This explicitly authorizes an inline operational command invoking the committed
checker's EXISTING authentication, _stream_table and metadata-component functions
on whole named real components. No new production/test/benchmark source file or
checker modification. Use PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python
with one inline heredoc; foreground terminal timeout600. No relaunch on timeout or
failure. Capture exact actual command, stdout/stderr/status in Record515. No full
check_release/main invocation and no .proofs output: this measures a bounded subset
and can NEVER claim a complete-release consumer proof or admission.

Before the measured loop, authenticate Python3.13, Nautilus2.0.0rc3/PyArrow25.0.0,
executing checker SHA and integrated blobs; seal_code_identity at original source
1f5629badfa0e8af6338fbeb019a5f7e60b6a324 with bind_runtime/executing paths exactly as
check_release does; _load_prepared on accepted candidate; require nonconsumable,
eleven manifests, 423446 references and1165116869 rows. Use _release_charge and
unchanged combined proof+scratch+publication headroom/reserve checks from checker.
Read-only catalog pre/post baseline: mode=ro exp003.db, queries below, json.dumps
rows with default=str,separators=(',',':'),ensure_ascii=False and SHA256 UTF8:

```
SELECT dataset_id, publication_uri FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id;
SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id;
```

Require Q0=0rows SHA4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945;
Q1=5rows SHAb4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103.
Mismatch stops before measurement; no catalog mutation. Report actual rows/counts.

Create only fresh, absent, nonsymlink owned scratch root
/home/lars/.cache/tmp/cex002_review513_consumer_scratch using _fresh_scratch.
No deletion/reuse of existing paths. Enforce the checker's 256MiB physical cap and
29,690,701,415 reserve on the actual SSD device; apply combined resource checks
including SQLite reservation, full future proof and8MiB publication allowances.
Accepted inputs stay read-only. Success cleans only authenticated batch files via
the existing helper; failed bounded partial state stays. Keep the empty root.

Select deterministically from the authenticated manifests in chain order. Group
TABLE refs within each manifest by partition.component (missing component is ""
only for the bundle, whose actual tag is absent). For each group select a whole
file with 0<=rows<=65536 by minimal (-rows,bytes,relative_path). If none qualifies,
ONLY the single harmonic-bundle table of178946rows is allowed as exception. No
other large table or source-row slicing. This yields24 tables /369588 rows. Verify
these totals before starting. Include all11 dataset types and all known component
groups, including154bar-gap rows, zero-row official fee schema, 59388depth rows,
59085ticker rows and the complete178946row bundle. Metadata refs are not table rows.
Also authenticate one smallest metadata ref per manifest (if present), with
_metadata_component; report their count separately, never as NT observations.

For EACH selected table: resolve only contained regular nonsymlink path, authenticate
_snapshot hash/bytes against spec, validate actual footer via _footer_from_partition
and manifest _registry_contracts, then invoke existing _stream_table with shared
scratch and monotonically increasing batch sequence. Native bars ONLY for bar dataset
role=partition/component=""; quality_gap uses custom transport. Enforce the same
explicit bar tag/role and mandatory primary schema guards as integrated checker.
After return require matching source/readback counts/digests/time and unchanged
_snapshot, then emit one compact JSON progress record with dataset, component,
path, physical bytes, source/readback rows, digests/time, elapsed_seconds and rows/sec.
No hash/time/source value assignment may replace actual queried data. Zero-row
schema is honestly zero; do not claim it transported fictional observations.

At terminal: selected counts reconcile; scratch measured zero; reauthenticate
candidate/manifests, original runtime code, checker hash and selected references;
read catalog Q0/Q1 unchanged; report elapsed by component and total, RSS high-water
(resource.getrusage RUSAGE_SELF ru_maxrss Linux KiB*1024), SSD free before/after,
actual zero final scratch and enforced cap. Do not label cap as measured peak disk.
Actual timings support a preliminary SCALE ESTIMATE ONLY; no promised full runtime
or release PASS. No instrumentation monkeypatch, retries, new proof, producer run,
accepted data mutation, admission, economic reinterpretation or next ticket.

### C — terminal measurement record and stop

After the sole measurement succeeds OR fails, publish only
research/sprint_004/515_CEX002_REAL_CONSUMER_MEASUREMENT_RECORD.md with exact command,
outputs/status, sampled selection, actual per-group throughput/resources, catalog
before/after and limitations; preserve all partials. On failure, only terminal
inspection/record publication is authorized, not repair/retry or further consumer
execution. Do not invent unobserved measurements or claim all release rows passed.
Require exact one-path stage, cached whitespace, normal commit/push, synchronized
HEAD/origin and empty index. Correct record whitespace only if needed. Stop for
reviewer inspection with both commits/results; no automatic full-release run.
