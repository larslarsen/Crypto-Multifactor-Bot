# CEX-002 Review 517 — One full consumer verification

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Next required actor: Jr Dev — Hermes
Architecture: ADR-0039 unchanged

## Decision and bounds

Review 513 accepts Record 516 / e8aa52611e32132587dc1a0f42d8432b9f3e62a3:
24 whole tables / 369,588 rows, all 11 dataset types and component groups,
matching genuine Nautilus readback, unchanged catalog and empty final scratch.
The component-weighted linear transport estimate for the full 1,165,116,869 rows
is approximately 49.24 hours, before additional overhead. No full proof exists.

The owner's continuation authorizes the reviewer to advance CEX-002. Authorize
Hermes to execute the integrated checker ONCE over the entire accepted candidate.
No developer or source change is needed. Keep the accepted clean Python 3.13 /
Nautilus 2.0.0rc3 / PyArrow 25.0.0 environment and all passed checks. Do not rerun
fixtures, lint, setup, installation or prior measurements.

Use native terminal(background=true, notify_on_complete=true, pty=false), then
native process retrieval for THAT session. Read-only inspection of the installed
terminal/process implementation confirms local tracked Popen execution does not
inherit the 600-second foreground limit. Use the external 345600-second (96-hour)
deadline below, allowing overhead above the preliminary estimate. Do not change
Hermes configuration, use shell detach wrappers, launch duplicates or retry.
This supersedes old foreground-only restrictions solely for this full run.
Keep the Hermes CLI alive while the job runs. A tool/CLI/host interruption is not
a successful result; preserve state and return to reviewer without restart.

## Frozen identities and resources

Candidate: 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34
Prepared descriptor: data/.cex002_harmonic_bundle/.prepared/8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.json
Original producer/catalog source: 1f5629badfa0e8af6338fbeb019a5f7e60b6a324
Checker integration: c189065fecacd446ab8681238675866585d38050
Checker: scripts/research/check_cex002_nautilus_consumer.py
Checker SHA256: ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117
Test SHA256: c4e051a1b9e0f9ae9df983f4319c2f4370cbe108b2d88b2632af8768d4465ff5

The unmodified checker authenticates every source, manifest, schema and component,
executes genuine custom/native readback, checks the complete 423,446-file closure,
and seals its existing strict v1 proof only after full reconciliation and terminal
source reauthentication. Expected table rows: 1,165,116,869. Prepared candidate
remains non-consumable. No catalog admission is part of this assignment.

Unchanged limits: scratch 268,435,456 bytes; proof 536,870,912 bytes; publication
8,388,608 bytes; operating reserve 29,690,701,415 bytes; release metadata remainder
4,985,471,619 bytes. Current metadata charge includes the unchanged 3,458,088,960-byte
SQLite reservation. Use the checker's existing combined release/reserve checks.
Do not enlarge batches or weaken a digest, time, authority or resource condition.
Fresh scratch: /home/lars/.cache/tmp/cex002_review517_full_consumer_scratch
Evidence: research/sprint_004/518_CEX002_FULL_CONSUMER_EXECUTION_RECORD.md
Both must be absent and nonsymlinks before launch; never delete/reuse old scratch.

## Ordered Hermes workflow

1. One grouped read-only preflight: require HEAD==origin/main and empty index;
   record actual HEAD/time, checker/test hashes, and equality of the three runtime
   source files to their blobs at 1f5629b. Authenticate the prepared descriptor's
   physical hash against its filename; require proof namespace absent, fresh scratch
   and evidence destinations, executable existing environment and /usr/bin/timeout,
   adequate SSD capacity and no existing full checker process (native process list
   plus local process listing). Do not run an import/version or fixture probe: the
   existing checker enforces its environment/identity/closure/reserve checks itself.
   Read exp003.db via SQLite mode=ro and capture BOTH exact queries below, their
   actual rows/counts and canonical JSON SHA256. Require the accepted pins before
   launch. A mismatch stops; do not repair or alter data.

```sql
SELECT dataset_id, publication_uri FROM dataset WHERE transform_name='cex002_reference_publication' ORDER BY dataset_id;
SELECT dataset_id, quality_status, publication_status, quality_summary_json FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%' ORDER BY dataset_id;
```

Canonical query result serialization: json.dumps(rows, default=str,
separators=(',', ':'), ensure_ascii=False), SHA256 of UTF8. Q0 count 0 /
4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945;
Q1 count 5 / b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103.

2. Only after preflight passes, run the following exact command ONCE using native
   terminal background=true, notify_on_complete=true, pty=false. The shell writes
   a fresh no-clobber Record 518 and captures all actual checker stdout/stderr plus
   checker/deadline and capture statuses. Preserve the raw block byte-for-byte.
   Normal one-operation approval may relay the owner's continuation; no permanent
   or session-wide grants or policy changes. First denial/failure stops.

```bash
cd /home/lars/Crypto_Multifactor_Bot
set -euo pipefail
record=research/sprint_004/518_CEX002_FULL_CONSUMER_EXECUTION_RECORD.md
if [ -e "$record" ] || [ -L "$record" ]; then
    printf 'Record 518 already exists or is a symlink\n' >&2
    exit 1
fi
set -o noclobber
exec 3> "$record"
set +o noclobber
exec 4>> /dev/fd/3
exec 3>&-
printf '# CEX-002 Record 518 — Full consumer execution\n\nLaunch UTC: ' >&4
date -u +'%Y-%m-%dT%H:%M:%SZ' >&4
printf 'Execution HEAD: ' >&4
git rev-parse HEAD >&4
printf '\n## Raw checker output\n\n```jsonl\n' >&4
set +e
PYTHONPATH=src /usr/bin/timeout --signal=TERM --kill-after=60s 345600s /tmp/cex002_nautilus_review511_env/bin/python -u scripts/research/check_cex002_nautilus_consumer.py --repo /home/lars/Crypto_Multifactor_Bot --candidate-sha 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34 --checker-sha ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117 --scratch-root /home/lars/.cache/tmp/cex002_review517_full_consumer_scratch 2>&1 | tee -a /dev/fd/4
pipeline_status=("${PIPESTATUS[@]}")
checker_status=${pipeline_status[0]}
capture_status=${pipeline_status[1]}
printf '```\n\nChecker/deadline exit status: %s\nOutput capture exit status: %s\n' "$checker_status" "$capture_status" >&4 || exit 1
exec 4>&-
if [ "$capture_status" -ne 0 ]; then
    exit "$capture_status"
fi
exit "$checker_status"
```

3. Retain the returned session_id/PID. Retrieve the SAME session once after initial
   startup; report actual status/progress and leave it running for completion
   notification. Do not block a model turn for days or run a polling loop. Later
   progress/status retrieval is allowed on owner continuation or completion notice.
   While running, no Record 518 commit or final-proof claim; the raw capture is live.

4. At terminal, preserve the exact terminal status. Nonzero/timeout/interruption:
   no retry, cleanup, repair, partial promotion or admission. On success, inspect
   the emitted proof's content hash/size, strict root/count totals, dataset/component
   row reconciliation, zero terminal scratch and unchanged candidate/source hashes.
   Do not invoke another full verifier or producer. The accepted checker itself
   performs the complete source/readback proof; inspecting its emitted document
   does not authorize an extra billion-row traversal. On either result, repeat the
   same read-only catalog queries, compare with preflight and disclose differences.

5. Append Hermes provenance/model, governing command, actual preflight and process
   identities, statuses/progress, terminal proof/resource/catalog observations and
   limitations AFTER the raw block; preserve all raw output. Publish ONLY Record 518
   after terminal with empty-index guard, exact-one-path staged equality, cached
   whitespace check, normal commit/push, HEAD==origin/main and empty-index proof.
   Preserve unrelated dirty paths. Stop for reviewer; do not alter handoff/ticket,
   accept the release, admit catalog rows, run replay/economic/final suites, or
   start another ticket. A failure still permits this terminal evidence publication.

## Reviewer publication scope

Reviewer may publish only this Review 517, docs/handoff/CURRENT_TASK.md and
tickets/CEX-002.md. Hermes alone owns command execution and Record 518 publication.
Reviewer may append the returned running process identity/status to this review and
handoff without changing the execution or treating launch as successful completion.
CEX-002 remains IN_PROGRESS; next ticket and its authorization remain NONE.


## Launch inspection — running, no terminal result

Hermes preflight messages 100101–100106 report synchronized execution HEAD
`2e7fadb34e2a434c44da6502c617c97490f04f47`, empty index, matching checker/test
and all three runtime-source pins, descriptor hash equal to the accepted candidate,
299,267,674,112 free SSD bytes, and fresh nonsymlink proof/scratch/evidence paths.
Both read-only catalog query digests/counts match the accepted pins. The first
process-count command included its own shell text; actual matching-process
inspection found zero checker processes. This was preflight clarification, not
a failed checker run. No setup or tests were repeated.

Hermes launched the exact reviewed command once at `2026-10-21T05:01:23Z`,
terminal messages 100107/100108: native session `proc_0c886acde04a`, PID `2343463`,
notify_on_complete=true. The first SAME-session poll, messages 100109/100110,
reports RUNNING at 67 seconds uptime. The live raw Record 518 contains the
`authenticated_descriptor` stage at 40.229 seconds and a later `roundtrip`
observation of 24,576 completed references / 283,250 rows at 126.044 seconds.
These are intermediate counters, not full-release success or a runtime forecast.

Do not relaunch. Keep the existing Hermes CLI/session alive and retrieve only
this tracked process on continuation/completion. Record 518 is live and uncommitted;
Hermes appends/publishes it only after terminal under the workflow above. The
96-hour deadline and all original guards remain active. Catalog admission, replay,
economic checks, final suites and ticket acceptance remain unassigned. Reviewer
publication here is only the previously enumerated three governance paths.


## Reviewer acceptance — full consumer proof completed

ACCEPT Record 518 at `8a47e787ac1999e9bb3f0c623b973be319ddacd9` and the
completed full consumer verification. Hermes received the tracked completion
notice, completed the already authorized terminal inspection/catalog comparison,
published only Record 518 and stopped. Reviewer inspected the exact one-path
commit, HEAD==origin/main, empty index and committed/worktree record equality.
Record SHA256: `1a62d03d63df5eeadb7d269d58cd095e1eb34e4db08a6558b4ff4d5e70b6951e`.
The retained raw capture has 415 structured progress records, terminal PASS, and
both checker/deadline and capture exit statuses 0. No run or test was repeated.

Actual elapsed time: 189,195.734 seconds (52 hours 33 minutes 16 seconds), within
the unchanged 96-hour deadline. All 423,446 components and 1,165,116,869 table
rows were reconciled. Scratch ended empty. Terminal metadata charge is
3,950,355,317 bytes, including the 264,156,517-byte proof and unchanged SQLite
reservation. All original resource limits remain satisfied.

Proof: data/.cex002_harmonic_bundle/.proofs/3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d.json
SHA256: 3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d
Size: 264,156,517 bytes.

Reviewer artifact inspection independently matched physical proof hash/filename/
size, PASS/complete_release root, accepted candidate/checker pins, 11 datasets,
178,947 table plus 244,499 metadata components and the exact total row count.
Every emitted component's source/readback row counts and logical digests match.
This inspection reads the emitted proof; it is not another source-data traversal
or acceptance-command execution. Current candidate/checker/test hashes match their
accepted pins and the scratch root contains no entries. Hermes's terminal Q0/Q1
counts/digests match preflight; the catalog remains unchanged.

The clean full-release Nautilus consumer check is complete and accepted. Preserve
its proof, Record 518 and all previous accepted evidence. The candidate remains
non-consumable and no catalog admission occurred. CEX-002 remains IN_PROGRESS:
remaining independent economic evidence, release admission/replay and original
final acceptance requirements still need reviewer disposition. Next required actor
is the Lead Quantitative Finance Researcher/Engineer; next ticket and its
authorization remain NONE. This checkpoint authorizes no new run or source change.
Reviewer publication remains limited to the three previously enumerated paths.
