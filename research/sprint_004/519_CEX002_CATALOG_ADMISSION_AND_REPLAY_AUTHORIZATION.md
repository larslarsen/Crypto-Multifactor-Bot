# CEX-002 Review 519 — Catalog admission, identical replay and release readback

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Next required actor: Jr Dev — Hermes
Architecture: ADR-0037 / ADR-0039 unchanged

## Decision

Review 517 accepts the complete Nautilus consumer proof and Record 518 at
8a47e787ac1999e9bb3f0c623b973be319ddacd9. All 1,165,116,869 rows across
423,446 references / 11 datasets passed. Preserve that result; no consumer rerun.
The owner's continuation authorizes advancing this ticket to its existing catalog
publication/replay requirement. No developer/source change is needed.

Hermes is authorized to run the unchanged production CLI for: ONE initial publish,
ONE intentional identical publish replay, then ONE explicit release-reader verify.
These are separate acceptance steps, not automatic retries. The production code
independently reauthenticates source values on each step; this may be lengthy but
never performs another Nautilus write/query traversal. No hash reuse or bypass of
that code is authorized. A complete catalog publication still does not constitute
final CEX-002 acceptance: remaining independent economic examples and original
final acceptance suites/report remain mandatory and unassigned here.

## Exact pins and permitted writes

Original integrated producer/catalog source: 1f5629badfa0e8af6338fbeb019a5f7e60b6a324
Candidate: 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34
Proof: 3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d
Proof bytes: 264,156,517
Checker SHA256: ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117
Nautilus version: 2.0.0rc3
Catalog: /home/lars/Crypto_Multifactor_Bot/exp003.db
Environment: /tmp/cex002_nautilus_review511_env/bin/python (reuse, no setup/install)

Use the production CLI only; no policy injection or authority override. It binds
runtime source to the original commit, authenticates candidate/proof/full typed
rows, durable final descriptor and every catalog field/file/dependency, and admits
all eleven datasets in one BEGIN IMMEDIATE transaction. Its replay requires an
identical complete catalog state. Its explicit verify uses the actual release reader.

Permitted data writes are the adapter's own lock/final content-addressed metadata
under data/.cex002_harmonic_bundle and its eleven dataset rows, 423,446 file rows
and ten dependency edges in exp003.db plus normal SQLite journals. The existing
proof is reused at its authenticated path. Accepted product/candidate/proof bytes,
the five quarantined BitMEX rows and all unrelated files remain unchanged.
Do not call prepare, rerun products, mutate SQL directly, repair conflicts, change
schemas/code/budgets, clean partial state, launch duplicates or retry a failure.

Keep operating reserve 29,690,701,415, metadata remainder 4,985,471,619,
publication allowance 8,388,608 and the original SQLite charge/multiplier unchanged.
The existing production guards enforce resource fit before catalog visibility.
Evidence destination: research/sprint_004/520_CEX002_CATALOG_ADMISSION_AND_REPLAY_RECORD.md
It must be absent and nonsymlink. Publication namespace must be absent before the
first admission. Preserve all old preparation/proof/measurement evidence.

## Ordered Hermes execution and publication

1. One grouped read-only preflight: require HEAD==origin/main, empty index, runtime
   three-file equality to their blobs at 1f5629b; candidate/proof physical hashes
   equal the exact pins above, proof size exact, and existing executable environment.
   Require no running prior checker/publisher process (show actual process identities,
   excluding only the checking shell) and fresh nonsymlink Record 520 / publication
   namespace. Record actual HEAD/time/free space and preserve unrelated dirty paths.
   The command below also checks candidate/proof and baseline catalog pins before
   calling the production CLI. No tests, setup, imports of production helpers,
   additional verifier, or data mutations in preflight. First mismatch/denial stops.

2. After preflight passes, execute the EXACT bash block below ONCE using native
   terminal(background=true, notify_on_complete=true, pty=false). It uses a tracked
   job and one 96-hour deadline for the whole ordered workflow, captures actual
   output in a fresh no-clobber Record 520, and stops on the first failed phase.
   The inline Python is operational orchestration of existing CLI commands and
   read-only SQLite/document observations; it creates no source/test/helper file.
   Native process retrieval is allowed for that same session only. Retrieve once
   after startup, report actual phase/status, then leave it running for completion
   notification. No polling loop or model turn blocked for days. A normal Allow once
   prompt may relay the authorized continuation; no permanent/session grants or
   approval-policy changes. Do not resubmit after denial.

```bash
cd /home/lars/Crypto_Multifactor_Bot
set -euo pipefail
record=research/sprint_004/520_CEX002_CATALOG_ADMISSION_AND_REPLAY_RECORD.md
if [ -e "$record" ] || [ -L "$record" ]; then
    printf 'Record 520 already exists or is a symlink\n' >&2
    exit 1
fi
set -o noclobber
exec 3> "$record"
set +o noclobber
exec 4>> /dev/fd/3
exec 3>&-
printf '# CEX-002 Record 520 — Catalog admission and replay\n\nLaunch UTC: ' >&4
date -u +'%Y-%m-%dT%H:%M:%SZ' >&4
printf 'Execution HEAD: ' >&4
git rev-parse HEAD >&4
printf '\n## Raw execution output\n\n```jsonl\n' >&4
set +e
/usr/bin/timeout --signal=TERM --kill-after=60s 345600s /tmp/cex002_nautilus_review511_env/bin/python -u - 2>&1 <<'RUN' | tee -a /dev/fd/4
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
import time

root = Path('/home/lars/Crypto_Multifactor_Bot')
candidate = '8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34'
proof = '3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d'
checker = 'ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117'
code = '1f5629badfa0e8af6338fbeb019a5f7e60b6a324'
base = root / 'data/.cex002_harmonic_bundle'
prepared_path = base / '.prepared' / (candidate + '.json')
proof_path = base / '.proofs' / (proof + '.json')
started = time.monotonic()
phase = 'preflight'

def emit(**items):
    print(json.dumps(items, sort_keys=True, separators=(',', ':'), default=str), flush=True)

def need(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def physical(path):
    need(path.is_file() and not path.is_symlink(), 'unsafe or missing pinned file')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 2**20), b''):
            h.update(chunk)
    return h.hexdigest(), path.stat().st_size

def snapshot(label):
    con = sqlite3.connect('file:' + str(root / 'exp003.db') + '?mode=ro', uri=True)
    try:
        con.execute('BEGIN')
        rows = con.execute("SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id").fetchall()
        qbody = json.dumps(rows, default=str, separators=(',', ':'), ensure_ascii=False)
        qsha = hashlib.sha256(qbody.encode()).hexdigest()
        need(len(rows) == 5 and qsha == 'b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103', 'quarantine state changed')
        selected = "SELECT dataset_id FROM dataset WHERE transform_name='cex002_reference_publication'"
        queries = {
            'dataset': "SELECT * FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id",
            'dataset_file': 'SELECT * FROM dataset_file WHERE dataset_id IN (' + selected + ') ORDER BY dataset_id, storage_uri',
            'dataset_input_dataset': 'SELECT * FROM dataset_input_dataset WHERE dataset_id IN (' + selected + ') ORDER BY dataset_id, input_dataset_id, role',
            'dataset_input_raw_object': 'SELECT * FROM dataset_input_raw_object WHERE dataset_id IN (' + selected + ') ORDER BY dataset_id, raw_object_id, role',
        }
        observed = {}
        for name, sql in queries.items():
            cursor = con.execute(sql)
            columns = [d[0] for d in cursor.description]
            digest = hashlib.sha256()
            digest.update((json.dumps(columns, separators=(',', ':')) + '\n').encode())
            count = 0
            for row in cursor:
                digest.update((json.dumps(row, default=str, separators=(',', ':'), ensure_ascii=False) + '\n').encode())
                count += 1
            observed[name] = {'count': count, 'sha256': digest.hexdigest()}
        ids = sorted(r[0] for r in con.execute(selected))
        observed['dataset_ids'] = ids
        observed['quarantine_sha256'] = qsha
        emit(stage='catalog_snapshot', label=label, snapshot=observed)
        return observed
    finally:
        if con.in_transaction:
            con.rollback()
        con.close()

try:
    need(physical(prepared_path)[0] == candidate, 'candidate physical pin changed')
    need(physical(proof_path) == (proof, 264156517), 'proof physical pin changed')
    descriptor = json.loads(prepared_path.read_bytes())
    expected_ids = sorted(d['dataset_id'] for d in descriptor['datasets'])
    need(len(expected_ids) == len(set(expected_ids)) == 11, 'candidate dataset count changed')
    initial = snapshot('before_admission')
    need(initial['dataset'] ['count'] == 0 and initial['dataset_ids'] == [], 'release already exists before initial admission')
    env = os.environ.copy()
    env['PYTHONPATH'] = 'src'
    common = ['--repo', str(root), '--catalog', str(root / 'exp003.db'), '--code-commit', code,
              '--proof', str(proof_path), '--proof-sha', proof, '--checker-sha', checker,
              '--nautilus-version', '2.0.0rc3']
    publication = None
    admitted = None
    for phase in ('admission', 'identical_replay', 'release_reader'):
        action = 'verify' if phase == 'release_reader' else 'publish'
        args = ['--publication-sha', publication] if action == 'verify' else ['--prepared-sha', candidate]
        cmd = [sys.executable, '-u', 'scripts/research/publish_binance_usdm_harmonic_bundle.py', action, *common, *args]
        emit(stage='phase_started', phase=phase, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), command=shlex.join(cmd))
        began = time.monotonic()
        result = subprocess.run(cmd, cwd=root, env=env, text=True, capture_output=True)
        emit(stage='phase_result', phase=phase, exit_code=result.returncode, elapsed_seconds=round(time.monotonic()-began, 3), stdout=result.stdout, stderr=result.stderr)
        need(result.returncode == 0, phase + ' failed; no further phase is authorized')
        found = result.stdout.strip()
        need(re.fullmatch('[0-9a-f]{64}', found) is not None, 'CLI did not return one publication identity')
        if publication is None:
            publication = found
        else:
            need(found == publication, 'publication identity changed across replay/readback')
        final_path = base / '.publication' / (publication + '.json')
        need(physical(final_path)[0] == publication, 'publication physical pin mismatch')
        final = json.loads(final_path.read_bytes())
        need(final.get('consumable') is True and final.get('prepared_sha256') == candidate, 'publication does not bind the candidate')
        need(final.get('proof_sha256') == proof and final.get('checker_source_sha256') == checker, 'publication proof/checker binding changed')
        current = snapshot(phase)
        need(current['dataset_ids'] == expected_ids, 'catalog dataset closure differs from candidate')
        need([current[n]['count'] for n in ('dataset','dataset_file','dataset_input_dataset','dataset_input_raw_object')] == [11,423446,10,0], 'catalog row/file/dependency closure mismatch')
        if admitted is None:
            admitted = current
        else:
            need(current == admitted, 'persisted catalog fields changed across replay/readback')
    need(physical(prepared_path)[0] == candidate and physical(proof_path) == (proof,264156517), 'candidate/proof changed at terminal')
    emit(stage='PUBLICATION_REPLAY_READBACK_COMPLETE_NOT_TICKET_ACCEPTANCE', publication_sha256=publication, prepared_sha256=candidate, proof_sha256=proof, dataset_count=11, file_count=423446, dependency_edges=10, elapsed_seconds=round(time.monotonic()-started,3), free_bytes=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize)
except BaseException as exc:
    emit(stage='FAILED', phase=phase, error_type=type(exc).__name__, error=str(exc))
    raise
RUN
pipeline_status=("${PIPESTATUS[@]}")
workflow_status=${pipeline_status[0]}
capture_status=${pipeline_status[1]}
printf '```\n\nWorkflow/deadline exit status: %s\nOutput capture exit status: %s\n' "$workflow_status" "$capture_status" >&4 || exit 1
exec 4>&-
if [ "$capture_status" -ne 0 ]; then
    exit "$capture_status"
fi
exit "$workflow_status"
```

3. On terminal, retain actual whole-job/deadline and capture statuses. If all phases
   succeed, inspect final publication hash/descriptor, the emitted equal publication
   IDs, 11/423446/10/0 catalog closure and byte-identical all-column catalog snapshot
   digests across replay/readback. Preserve proof/candidate pins and unchanged five-row
   quarantine digest. The readback command is the independent production reader;
   do not run it again or repeat any other passed phase. On failure, preserve all
   raw output/partial state and report the exact phase. No retry, repair, rollback
   of a committed release by hand, cleanup, or promotion of a partial result.

4. Append actual provenance/model, Review519 execution HEAD/command, preflight,
   process/phase identities, elapsed/status/output, publication/catalog/resource
   results and limitations AFTER the raw block. Publish ONLY Record 520 after
   terminal: empty index, exact-one-path staged equality, cached whitespace check,
   normal commit/push, HEAD==origin/main and empty index, then STOP for reviewer.
   A failure permits the same terminal record-only publication. Do not update the
   handoff/ticket, accept CEX-002, run economic/final suites or start another ticket.

## Reviewer governance publication scope

Exactly this Review 519, docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md.
Reviewer may record the returned process identity/observed phase in these same paths.
Hermes exclusively owns execution, implementation evidence and Record 520 Git.
CEX-002 remains IN_PROGRESS; next ticket and its authorization remain NONE.
