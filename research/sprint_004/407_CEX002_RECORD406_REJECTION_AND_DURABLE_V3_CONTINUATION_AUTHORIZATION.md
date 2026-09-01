# CEX-002 Record-406 Rejection and Durable V3 Continuation Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept bounded safe facts; reject false checkpoint and runner-compliance claims; authorize one durable continuation of the existing v3 tree
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted publication and safe facts

The reviewer accepts Hermes commit `d93786a95f96869c4a9a0ac6784f0d55289836ab` only as the
exact three-path publication of record 406 plus the two control-plane paths. `HEAD == origin/main`
at that commit, staging is empty, and the same 11 unrelated modified plus 13 unrelated untracked
paths remain unstaged.

The following bounded record-406 facts are accepted:

- the Review-405 path-explicit preflight passed at
  `4fd3b7896909771fad13dab83a69bb5c894836d5`;
- one fresh v3 planner was launched at `2026-09-01T09:31:27Z` through runner directory
  `/tmp/runner_406_9Lp50Y`;
- the planner issued listing-only work and created a partial fixed v3 tree;
- the Hermes harness called `process.kill` after about 34.7 minutes and observed status `-15`
  (`SIGTERM`); no duplicate or replacement invocation was launched;
- no v3 locator, receipt, manifest, or lineage was published; and
- no candidate, acquisition, Gate-2 acceptance, transition, later gate, or next ticket resulted.

The external kill consumed Review 405's one invocation. It did not produce a candidate.

## Rejected checkpoint claims

Record 406 and CURRENT_TASK call pass 1 complete and its cursor null. Those claims are false. The
reviewer read the append-only partial checkpoint without opening its private SQLite index. Its
exact current SHA-256 is
`2bea7abc8c5d398b6380a1ed788fd8d86bcac320f55cf0d6c228007d99c0b279`, and it records:

| Field | Exact checkpoint value |
| --- | --- |
| schema | `cex002_gate2_revision_candidate_checkpoint_v3` |
| `pass_1.listing_complete` | `false` |
| `pass_1.published_pages` | `1468` |
| `pass_1.discovered_prefixes` count | `1308` |
| `pass_1.completed_prefixes` count | `953` |
| `pass_1.cursor.prefix` | `data/futures/um/daily/metrics/NTRNUSDT/` |
| `pass_1.cursor.continuation_token` | `1aPFwVS7w4ap5r0zrkTH6OipgxhIVX3AhV07R7eI6mlTtkZTlf7aSewmf1U3ViqLCkR/4iI+xqmkBJ2l62SmhTgUgtm/eDZtAWc9IvTdEofx1pc1qsAxnZrZZWpagxjz0k4Q8wMUYl0I=` |
| `pass_2.listing_complete` | `false` |
| `pass_2.published_pages` | `0` |
| `pass_2.discovered_prefixes` count | `2` |
| `pass_2.completed_prefixes` count | `0` |
| `pass_2.cursor.prefix` | `data/futures/um/daily/bookTicker/` |
| `pass_2.cursor.continuation_token` | `null` |

Pass 1 stopped in the middle of a paginated aggregate prefix. Pass 2 was initialized in the
checkpoint but issued no published page. A null continuation token inside pass 2's initial cursor
does not mean the pass completed. Record 406's statements that pass 1 completed, had a null
cursor, and that traversal completed are rejected. The same statements in CURRENT_TASK are
superseded by this review.

The partial tree contains exactly 1,468 page files, an empty `candidate.lock`, and the private
index `tmp/listing.sqlite` at 396,005,376 bytes with SHA-256
`712415cc1a7f44306e7e45200d61e5902b0a0ea474c82c0fd95c021ce87ec3d4`. There are no publication
files. Hashing the private index did not open or query it.

## Rejected runner-compliance claims

Review 405 required at least four hours wall allowance, observation of the same process to natural
terminal, separate shell and planner PID/start-tick identities, and complete terminal capture.
Record 406 instead proves that Hermes called `process.kill` after about 34.7 minutes, well before
the allowance, while the planner was still inside pass 1. That action violated the authorization.

The runner evidence is also incomplete:

- `run.sh` SHA-256 is
  `6b5f11e054edeada9c7cea2edffe2419c6669596b4b1e4c0209ea251f981e868`;
- `stdout.txt` is only the 262-byte launch header, SHA-256
  `10214a923167a3623e74b1eb985a6883e329c37a6f050d76de63f9cda8f72fe4`;
- `stderr.txt` is empty, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- the runner captured no terminal trailer or exact end UTC because the shell itself was killed;
- `START_TICKS` came from `date +%s%N`, so it is wall-clock nanoseconds rather than Linux process
  start ticks from field 22 of `/proc/<pid>/stat`; and
- no separate planner PID/start ticks were captured.

Therefore `-15` is accepted only as the Hermes process-handle status after its explicit kill, not
as a runner-captured planner exit. Record 406 is not accepted as an exact compliant execution
record. It remains unchanged as rejected evidence; this append-only review is controlling.

## One durable continuation authorization

The partial v3 checkpoint is deterministic resume state created by the accepted v3 implementation.
No software architecture or financial-semantic change is made here, so no new ADR is required.
Hermes is authorized for exactly one continuation invocation against the existing fixed v3 tree.

Before launch Hermes must:

1. read `AGENTS.md`, CURRENT_TASK, the full CEX-002 ticket, ADR-0033, and Reviews 405-407;
2. prove `HEAD == origin/main` at this review's publication commit, staging empty, and no live
   revision-candidate planner;
3. rehash the five literal code paths and immutable v1/v2 checkpoint/private-index paths exactly
   as specified by Review 405;
4. without opening any SQLite database, prove the exact partial v3 checkpoint and private-index
   hashes, bytes, page count, publication absence, and checkpoint fields recorded above; and
5. stop and publish the mismatch if any required fact differs.

If preflight passes, Hermes creates one new `mktemp -d` runner and starts exactly this command once:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

The planner is expected to authenticate and resume the fixed partial v3 tree. The runner must:

- capture its exact script and separate immutable metadata/streams;
- capture start/end UTC and exit status;
- capture shell PID and planner PID plus each real Linux start tick from field 22 of that process's
  `/proc/<pid>/stat` entry;
- launch the planner as a child, wait for that exact child, and write a terminal trailer atomically;
- use `setsid` plus fully redirected `nohup` (or an equivalently durable detachment) so the
  one-shot Hermes turn can return without terminating the runner; and
- have no automated cutoff below four hours. Hermes must not call `process.kill`, send a signal,
  or terminate the runner merely because its own one-shot turn is ending.

After launch, Hermes verifies the recorded PIDs/start ticks and that the exact planner is live, then
returns without publication and without killing it. Read-only reviewer observation of the
checkpoint is permitted. Any later Hermes observation must identify the same shell/planner by both
PID and start ticks; it may not launch a replacement. Natural exit, a runner-recorded timeout of at
least four hours, disappearance, host interruption, or power loss consumes the continuation.

The continuation may only acquire accepted locks; authenticate generation 0 and the partial v3
state; issue the fixed official Binance S3 ListObjectsV2 requests; authenticate retained
sidecars/content; and finish or extend the existing v3 evidence tree. It may not reference or
mutate v1/v2; GET raw ZIPs; use Coinalyze; edit source/tests or generation 0; invoke acquisition;
clean or replace data; transition; start a later gate; or launch another invocation.

## Mandatory record 408 and stop

After the exact runner reaches terminal, Hermes may perform only bounded stat/hash/JSON inspection
of runner and v3 files; it may not directly query any real SQLite database. It must publish
`research/sprint_004/408_CEX002_DURABLE_V3_CONTINUATION_RECORD.md` with:

- the complete preflight and exact resume-state facts;
- runner script/hash/bytes, correct shell/planner PID/start ticks, complete streams, exact
  start/end/elapsed/allowance, terminal status, and exactly-once proof;
- exact checkpoint/page/pass/cursor/publication facts for non-completion; or all complete v3
  artifact, semantic, reachability, pending, classification, byte, capacity, code/generation, and
  false-authorization facts for completion; and
- explicit confirmation that no candidate was accepted and no acquisition or transition was
  attempted.

Before repository control Hermes sets both literal top-level actor fields to the reviewer and
writes exact final summaries. It then runs only:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/408_CEX002_DURABLE_V3_CONTINUATION_RECORD.md tickets/CEX-002.md
```

If both pass, Hermes commits/pushes exactly record 408 and the two control-plane paths, proves
remote equality, and stops. Candidate/runner/data bytes and every unrelated dirty path remain
unstaged. Harness output is a handoff only; only a later repository review may accept or reject the
candidate or authorize acquisition.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/407_CEX002_RECORD406_REJECTION_AND_DURABLE_V3_CONTINUATION_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No source/test, implementation evidence, candidate/runner/data, acceptance command, or unrelated
dirty path is included.
