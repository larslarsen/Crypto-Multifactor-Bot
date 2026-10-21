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


## Execution-command preparation clarification

To reduce Jr integration latency, the same sole GPT-6 Sol High senior may provide
read-only assistance: return the exact single inline operational command for B in
its response, with NO file edits, execution, imports/probes, tests, Git, records,
install or data work. No writable path or architecture is added. The reviewer
checks this command against B's fixed contract and relays it to Hermes for the
one authorized execution after A. Hermes remains sole executor/evidence/Git owner.
This does not authorize a second measurement, script file or proof. A preparation
interruption while no validation/data command ran changes none of the passed checks.


## A accepted; exact B command ready and output retention clarified

Accept integration c189065fecacd446ab8681238675866585d38050 and Record514.
Reviewer independently verified its exact three-path commit and both frozen
committed hashes; native100031/100032 confirm normal push, synchronized HEAD/origin
and empty index. The reviewer preparation interrupt occurred with no test, data
or validation command active. Preserve all passed checks; do not repeat A.

The senior returned the exact single inline B command without file edits or
execution. The reviewer statically checked it against B and relays its full text
directly to Hermes. No Jr redesign or API research is needed. Terminal tool timeout
is600; there is no second GNU timeout wrapper. Record515 may be created safely at
measurement start solely to retain the complete actual combined stdout/stderr.
Use the returned no-clobber held-descriptor/tee wrapper, pipe statuses and raw
code fence; append the actual command, interpretation/status/limitations after
terminal. Do not truncate, reconstruct or overwrite raw output and do not create
another log/source file. This is the already enumerated Record515 path; its small
output is covered by the unchanged8MiB future-publication allowance. Scratch has
its separate256MiB cap and must drain to zero. No proof/admission, full-run launch
or retry. Hermes resumes ONLY B/C now, then stops for reviewer inspection.


## Exact reviewed B command

Prepared as command text by the authorized GPT-6 Sol High senior and statically
reviewed by GPT-6.1. The oversized terminal prompt was rejected before delivery;
no measurement ran. Retain the literal operational command here for a short,
reviewable invocation by Hermes. This is the SAME sole B measurement, not new
software/test source, another execution or a permission bypass. Use terminal
foreground timeout600; preserve the raw Record515 output and all B/C stop rules.

```bash
cd /home/lars/Crypto_Multifactor_Bot || exit 1
record=research/sprint_004/515_CEX002_REAL_CONSUMER_MEASUREMENT_RECORD.md
if [ -e "$record" ] || [ -L "$record" ]; then
    printf 'Record 515 already exists or is a symlink\n' >&2
    exit 1
fi
set -o noclobber
exec 3> "$record" || exit 1
set +o noclobber
exec 4>> /dev/fd/3 || exit 1
exec 3>&-
printf '# CEX-002 Review 513 bounded real consumer measurement\n\n## Raw terminal output\n\n```text\n' >&4 || exit 1
set -o pipefail
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python - 2>&1 <<'PY' | tee -a /dev/fd/4
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import resource
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import pyarrow as pa

from scripts.research import check_cex002_nautilus_consumer as c

repo = Path("/home/lars/Crypto_Multifactor_Bot")
catalog_path = repo / "exp003.db"
scratch_path = Path("/home/lars/.cache/tmp/cex002_review513_consumer_scratch")
candidate = c.CANDIDATE_SHA256
checker_hash = "ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117"
test_hash = "c4e051a1b9e0f9ae9df983f4319c2f4370cbe108b2d88b2632af8768d4465ff5"
q0_sql = "SELECT dataset_id, publication_uri FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id;"
q1_sql = "SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id;"
q0_pin = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
q1_pin = "b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103"
started = time.monotonic()

def need(condition, message):
    if not condition:
        raise RuntimeError(message)

def emit(**values):
    print(json.dumps(values, default=str, separators=(",", ":"), ensure_ascii=False), flush=True)

def sha(body):
    return hashlib.sha256(body).hexdigest()

def integrated_blobs():
    for relative, expected in (
        ("scripts/research/check_cex002_nautilus_consumer.py", checker_hash),
        ("tests/test_cex002_nautilus_consumer.py", test_hash),
    ):
        working = (repo / relative).read_bytes()
        committed = subprocess.run(
            ["git", "-C", str(repo), "show", f"HEAD:{relative}"],
            check=True, capture_output=True,
        ).stdout
        need(sha(working) == expected and committed == working,
             f"integrated blob mismatch: {relative}")

def catalog_snapshot():
    db = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        result = []
        for sql in (q0_sql, q1_sql):
            rows = db.execute(sql).fetchall()
            encoded = json.dumps(
                rows, default=str, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            result.append((rows, sha(encoded)))
        return tuple(result)
    finally:
        db.close()

need(sys.version_info[:2] == (3, 13), "Python version changed")
need(importlib.metadata.version("nautilus-trader") == c.NAUTILUS_VERSION,
     "Nautilus version changed")
need(pa.__version__ == c.PYARROW_VERSION, "PyArrow version changed")
need(not Path(c.__file__).is_symlink(), "executing checker is a symlink")
need(c._sha(Path(c.__file__).read_bytes()) == checker_hash,
     "executing checker changed")
integrated_blobs()

runtime_sources = {
    "src/cryptofactors/catalog/dataset/cex002_reference_release.py":
        repo / "src/cryptofactors/catalog/dataset/cex002_reference_release.py",
    "src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py":
        repo / "src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py",
    "scripts/research/publish_binance_usdm_harmonic_bundle.py":
        repo / "scripts/research/publish_binance_usdm_harmonic_bundle.py",
}
code = c.seal_code_identity(
    repo, c.SOURCE_COMMIT, bind_runtime=True, executing=runtime_sources
)
descriptor, manifests = c._load_prepared(repo, candidate)
need(descriptor.get("consumable") is False and len(manifests) == 11,
     "candidate is not the complete non-consumable preparation")
need(all(manifest.code == code for manifest in manifests),
     "manifest code identity changed")
need(sum(len(manifest.files) for manifest in manifests) == c.EXPECTED_FILES,
     "referenced file closure changed")
need(sum(spec.rows for manifest in manifests for spec in manifest.files)
     == c.EXPECTED_ROWS, "referenced row closure changed")

bundle_bytes, charged, _incoming, subtotals = c._release_charge(
    repo, manifests, []
)
need(
    charged + c.PROOF_MAX_BYTES + c.SCRATCH_CAP_BYTES
    + c.PUBLICATION_ALLOWANCE_BYTES <= c.RELEASE_METADATA_REMAINDER_BYTES,
    "combined release capacity changed",
)
need(scratch_path.is_absolute() and not scratch_path.exists()
     and not scratch_path.is_symlink(), "scratch root is not fresh")
same_device = repo.stat().st_dev == scratch_path.parent.stat().st_dev
c._reserve(
    repo,
    c.PROOF_MAX_BYTES + c.PUBLICATION_ALLOWANCE_BYTES
    + subtotals["sqlite_bytes"]
    + (c.SCRATCH_CAP_BYTES if same_device else 0),
)
ssd_free_before = c._free(scratch_path.parent)
repo_free_before = c._free(repo)

before_catalog = catalog_snapshot()
need(len(before_catalog[0][0]) == 0 and before_catalog[0][1] == q0_pin,
     "catalog Q0 baseline changed")
need(len(before_catalog[1][0]) == 5 and before_catalog[1][1] == q1_pin,
     "catalog Q1 baseline changed")
for index, (rows, digest) in enumerate(before_catalog):
    emit(stage="catalog_before", query=f"Q{index}", count=len(rows),
         sha256=digest, rows=rows)

selected = []
metadata = []
contracts_by_id = {}
for manifest in manifests:
    contracts_by_id[manifest.dataset_id] = c._registry_contracts(manifest)
    groups = defaultdict(list)
    metadata_refs = []
    for spec in manifest.files:
        kind = spec.partition.get("kind")
        if kind == "metadata":
            metadata_refs.append(spec)
            continue
        need(kind == "table", "unknown referenced component kind")
        if manifest.dataset_type == "binance_usdm_harmonic_bundle":
            need("component" not in spec.partition,
                 "bundle component tag changed")
            component = ""
        else:
            component = spec.partition.get("component")
            need(type(component) is str,
                 "non-bundle table component tag absent or malformed")
        groups[component].append(spec)
    for component in sorted(groups):
        group = groups[component]
        eligible = [spec for spec in group if 0 <= spec.rows <= c.MAX_ROWS]
        if eligible:
            chosen = min(
                eligible,
                key=lambda spec: (-spec.rows, spec.bytes, spec.relative_path),
            )
        else:
            need(
                manifest.dataset_type == "binance_usdm_harmonic_bundle"
                and component == "" and len(group) == 1
                and group[0].rows == 178_946,
                "unapproved table exceeds the whole-file selection bound",
            )
            chosen = group[0]
        selected.append((manifest, component, chosen))
    if metadata_refs:
        chosen_metadata = min(
            metadata_refs, key=lambda spec: (spec.bytes, spec.relative_path)
        )
        metadata.append((manifest, chosen_metadata))

need(len(selected) == 24 and sum(spec.rows for _, _, spec in selected) == 369_588,
     "bounded selection count or rows changed")
selected_by_group = {
    (manifest.dataset_type, component): spec.rows
    for manifest, component, spec in selected
}
for key, expected_rows in (
    (("binance_usdm_bar_1h", "quality_gap"), 154),
    (("binance_usdm_cost_calibration", "official_fee_schedule"), 0),
    (("binance_usdm_cost_calibration", "retained_book_depth"), 59_388),
    (("binance_usdm_cost_calibration", "retained_book_ticker"), 59_085),
    (("binance_usdm_harmonic_bundle", ""), 178_946),
):
    need(selected_by_group.get(key) == expected_rows,
         f"required measured component changed: {key}")
emit(stage="selection", tables=len(selected), rows=369_588,
     metadata_refs=len(metadata), dataset_types=len(manifests),
     bundle_bytes=bundle_bytes, metadata_charge_bytes=charged,
     sqlite_reservation_bytes=subtotals["sqlite_bytes"],
     scratch_cap_bytes=c.SCRATCH_CAP_BYTES,
     proof_allowance_bytes=c.PROOF_MAX_BYTES,
     publication_allowance_bytes=c.PUBLICATION_ALLOWANCE_BYTES)

scratch = c._fresh_scratch(scratch_path, repo)
c._reserve(scratch, c.SCRATCH_CAP_BYTES)
sequence = 0
completed_rows = 0
verified = []
elapsed_by_component = {}
for manifest, component, spec in selected:
    path = c._relative(repo, spec.relative_path)
    initial = c._snapshot(repo, spec.relative_path)
    need((initial.sha256, initial.byte_size) == (spec.sha256, spec.bytes),
         "selected table bytes changed")
    c._footer_from_partition(
        path, spec, contracts_by_id[manifest.dataset_id]
    )
    native = False
    if manifest.dataset_type == "binance_usdm_bar_1h":
        need(spec.partition.get("role") == "partition",
             "bar table role changed")
        need(
            "component" in spec.partition
            and type(spec.partition["component"]) is str
            and spec.partition["component"] in {"", "quality_gap"},
            "bar table component changed",
        )
        native = component == ""
        if native:
            import pyarrow.parquet as pq
            need(
                {"venue_symbol", "open_time", "close_time", "open",
                 "high", "low", "close", "volume"}
                <= set(pq.ParquetFile(path).schema_arrow.names),
                "primary bar schema lacks native projection",
            )
    component_started = time.monotonic()
    proof_component, sequence = c._stream_table(
        scratch, sequence, path, spec, native
    )
    elapsed = time.monotonic() - component_started
    need(
        proof_component["source_row_count"]
        == proof_component["readback_row_count"]
        == spec.rows,
        "source/readback row mismatch",
    )
    need(
        proof_component["source_value_sha256"]
        == proof_component["roundtrip_value_sha256"],
        "source/readback digest mismatch",
    )
    need(
        proof_component["physical_sha256"] == spec.sha256
        and proof_component["physical_bytes"] == spec.bytes,
        "selected table physical identity mismatch",
    )
    need(c._snapshot(repo, spec.relative_path) == initial,
         "selected table changed during transport")
    verified.append((spec, initial))
    completed_rows += spec.rows
    elapsed_by_component[f"{manifest.dataset_type}:{component}"] = elapsed
    emit(
        stage="component", dataset_type=manifest.dataset_type,
        component=component, relative_path=spec.relative_path,
        physical_bytes=spec.bytes, source_rows=proof_component["source_row_count"],
        readback_rows=proof_component["readback_row_count"],
        source_value_sha256=proof_component["source_value_sha256"],
        roundtrip_value_sha256=proof_component["roundtrip_value_sha256"],
        time_start=proof_component["time_start"],
        time_end=proof_component["time_end"],
        time_absence_reason=proof_component["time_absence_reason"],
        elapsed_seconds=round(elapsed, 6),
        rows_per_second=round(spec.rows / elapsed, 3) if elapsed > 0 else None,
    )

for manifest, spec in metadata:
    initial = c._snapshot(repo, spec.relative_path)
    need((initial.sha256, initial.byte_size) == (spec.sha256, spec.bytes),
         "selected metadata bytes changed")
    component = c._metadata_component(spec)
    need(component["source_row_count"] == component["readback_row_count"] == 0,
         "metadata was counted as observations")
    need(c._snapshot(repo, spec.relative_path) == initial,
         "selected metadata changed during measurement")
    verified.append((spec, initial))
    emit(stage="metadata", dataset_type=manifest.dataset_type,
         relative_path=spec.relative_path, physical_bytes=spec.bytes,
         physical_sha256=spec.sha256, source_rows=0, readback_rows=0,
         value_identity=component["value_identity"])

need(len(selected) == 24 and completed_rows == 369_588,
     "measured selection did not reconcile")
need(c._scratch_bytes(scratch) == 0,
     "authenticated scratch was not fully drained")
again, current = c._load_prepared(repo, candidate)
need(again == descriptor and current == manifests,
     "candidate or manifests changed at terminal")
need(
    c.seal_code_identity(
        repo, c.SOURCE_COMMIT, bind_runtime=True, executing=runtime_sources
    ) == code,
    "runtime code identity changed at terminal",
)
need(c._sha(Path(c.__file__).read_bytes()) == checker_hash,
     "checker source changed at terminal")
integrated_blobs()
for spec, initial in verified:
    need(c._snapshot(repo, spec.relative_path) == initial,
         "selected reference changed at terminal")
after_catalog = catalog_snapshot()
need(after_catalog == before_catalog, "read-only catalog baseline changed")
for index, (rows, digest) in enumerate(after_catalog):
    emit(stage="catalog_after", query=f"Q{index}", count=len(rows),
         sha256=digest, rows=rows)
c._reserve(scratch, 0)
c._reserve(repo, subtotals["sqlite_bytes"])
emit(
    stage="MEASUREMENT_COMPLETE_NOT_RELEASE_PASS",
    tables=len(selected), table_rows=completed_rows,
    metadata_components=len(metadata), batch_sequence=sequence,
    elapsed_seconds=round(time.monotonic() - started, 6),
    elapsed_by_component_seconds={
        key: round(value, 6) for key, value in elapsed_by_component.items()
    },
    rss_high_water_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    ssd_free_before_bytes=ssd_free_before,
    ssd_free_after_bytes=c._free(scratch),
    repo_free_before_bytes=repo_free_before,
    repo_free_after_bytes=c._free(repo),
    final_scratch_bytes=c._scratch_bytes(scratch),
    scratch_cap_bytes=c.SCRATCH_CAP_BYTES,
    catalog_q0_sha256=after_catalog[0][1],
    catalog_q1_sha256=after_catalog[1][1],
)
PY
pipeline_status=("${PIPESTATUS[@]}")
python_status=${pipeline_status[0]}
tee_status=${pipeline_status[1]}
printf '```\n\nPython exit status: %s\nOutput capture exit status: %s\n' "$python_status" "$tee_status" >&4 || exit 1
exec 4>&-
if [ "$tee_status" -ne 0 ]; then
    exit "$tee_status"
fi
exit "$python_status"
```


## Execution gate blocked before measurement

Native terminal call100041 attempted the exact committed-document invocation;
result100042 was status=blocked, exit_code=-1, no stdout. The approval gate stated:
"BLOCKED: User denied this command. The user has NOT consented to this action."
This is the tool's stated reason; no owner message independently denying the action
was received in this conversation. The reviewer requested explicit owner execution
consent through the question UI and will not infer it from silence or prior generic
continuation. No retry, rephrased command or alternate consumer route is authorized
while that answer is pending.

Native100044/100046 read-only postchecks confirm Record515, owned scratch root and
.proofs absent, both source hashes unchanged, source/test/Record514 tracked-clean,
HEAD==origin/main and empty index. No real consumer measurement or proof ran; no
throughput, RSS, final-run resource result or full runtime estimate exists. A and
its27-case/scoped-check integration remain accepted.

The reviewer directs only C's previously authorized terminal evidence publication:
Record515 must disclose the denied invocation/status and no execution, preserve
postcheck observations, and stop. This does not approve measurement retry or alter
accepted source/data. After its publication the reviewer may accept that evidence
as a stopped gate, not as consumer success. Any later execution requires explicit
owner consent plus a fresh reviewer-bounded action, retaining the failure record.


## Unintended clarify-menu default corrected; no execution consent

Native clarify100047 recorded its default first option as approval even though
the reviewer's supplied response explicitly chose terminal-record-only. This
was a menu-input error, not owner execution consent. Native100048 announced an
intended retry, but no retry tool call was emitted. The reviewer immediately
interrupted the model and explicitly limited the new prompt to terminal Record515
publication only, with no retry/alternate measurement or further clarify menu.
Read-only inspection still finds Record515/scratch/.proofs absent at that point.
The external owner approval question remains unanswered; all prior execution-gate
restrictions remain. The terminal record must preserve this correction rather than
attribute an execution approval to the owner. No consumer result is claimed.


## Terminal evidence accepted; execution consent remains pending

Accept Record515 publication a47ee0c5de2439cd95eff14d3b6267f3be4f5c85 as a
blocked-before-execution terminal record, not a consumer result. Reviewer verified
the exact one-path commit, record SHA256
80484f094e46c7189240363360c46e74366800557d21a278d7f94d79d8b7c3e0,
normal push/HEAD==origin/main and empty index. Native100055/100057 confirm source
hashes unchanged and scratch/.proofs still absent. Hermes has completed C.

Precision qualification: Record515's displayed logical invocation omits only the
native tool's `cd /home/lars/Crypto_Multifactor_Bot &&` CWD preface. Its phrase
"executed as a single foreground terminal call" means submitted to that tool;
the gate rejected it before process execution. The native status was blocked,
exit_code=-1, empty stdout. No measurement executed and no values/throughput/RSS
or real-release reconciliation is available. Retain the accidental menu-default
correction; it is not owner consent.

The accepted source correction is c189065/Record514 with27 senior cases and scoped
checks; the blocked measurement is preserved separately in Record515. Explicit
owner approval requested in the question UI is still unanswered. Do not retry,
rephrase or use an alternate consumer route. Any later owner-approved measurement
must retain Record515 and use a fresh enumerated evidence destination rather than
overwrite it, with reviewer authorization before execution. CEX-002 remains
IN_PROGRESS, next ticket NONE; reviewer owns resolving the execution-consent gate.
