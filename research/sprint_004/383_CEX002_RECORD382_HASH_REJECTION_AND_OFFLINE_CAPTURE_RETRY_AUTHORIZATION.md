# CEX-002 Record-382 Hash Rejection and Offline Capture Retry Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject record 382's code-identity claims; accept its bounded partial-state facts; authorize one offline continuation with durable terminal capture
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Record-382 review

Hermes commit `4dd0ffe7e4d6675b8cfd685389f8c7fbdf21647b` contains exactly record 382
and the two control-plane paths, is present at both `HEAD` and `origin/main`, and leaves staging
empty. Record 382 contains exact zero results for its repository-control and scoped-diff commands
with correct Hermes attribution. Those publication facts are accepted.

Record 382's code-identity evidence is rejected. In four fields it substitutes or corrupts the
accepted values while claiming that all identities match Review 373:

| Field | Record 382 | Correct SHA-256 |
| --- | --- | --- |
| Production path | `8cef6be834b9a61c6ffdda38e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` | `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` |
| CLI path | `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` |
| Checkpoint planner CLI | `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` |
| Checkpoint planner source | `8cef6be834b9a61c6ffdda38e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` | `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` |

The phrase `Locator directory exists` is also rejected: the existing object is the candidate
root; the exact `locator.json` is absent. The pre-run page-set paragraph correctly changes its
derivation to the authenticated append-only post-run graph plus record 380, but then incorrectly
calls the nonexistent old checkpoint file unchanged. Review 383 supersedes that sentence. The
pre-run inventory digest is
`eadf3d73c08ab4bcb004724787a16ea4544096450ab4ec9bc823f9665379ad5c`; the post-run
inventory digest is
`ff27a8091cdcb2a4f5834c28d1698ad9057bff21b85f9f378beeb4bbe3127dce`. Each is SHA-256
over the UTF-8 LF stream of `LC_ALL=C` sorted unique lowercase content-address filenames, one
filename per line. The pre-run set is reconstructed from the first 640 entries of the current
authenticated append-only `pass_1.graph`, with record 380 supplying the boundary and count.

Bounded reviewer inspection independently confirms the durable partial state and therefore
accepts those facts from record 382:

- checkpoint SHA-256
  `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`,
  7,898,301 bytes;
- private SQLite SHA-256
  `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`,
  1,147,912,192 bytes;
- both independent passes are `listing_complete=true`, each with 1,308 completed/discovered
  prefixes, 2,093 graph pages, and a null cursor;
- 3,342 unique content-addressed physical page files; and
- candidate root present, with manifest, receipt, lineage, and `locator.json` absent.

The process was first observed absent at `2026-09-01T03:10:22Z`, but its exit code, stop reason,
stdout, and stderr were lost with the process-tool session. The abnormal unobserved terminal
classification is accepted. A candidate is not accepted and Gate 2 has not passed.

## One offline continuation with durable capture

Static inspection confirms that a checkpoint with both passes complete returns from both
listing loops after authenticating/rebuilding retained pages; it does not make a ListObjectsV2
request. Hermes is authorized for exactly one further invocation of the same planner solely to
obtain the deterministic post-listing terminal result and, if successful, publish the candidate:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before launch, Hermes must read `AGENTS.md`, `CURRENT_TASK.md`, CEX-002, ADR-0031, and records
381-383; prove `HEAD == origin/main` at this review's publication commit; prove staging empty and
no planner process live; rehash the three code paths to the correct values above; and reprove the
checkpoint, private-SQLite, page-inventory, complete-pass, and absent-locator facts above. A
mismatch stops before launch and is recorded.

The execution is offline with respect to provider transport: it may query-only authenticate
generation 0; rehash and rebuild from retained checkpoint/pages/private index; read retained
sidecars/content through the accepted held roots; compare the two complete listing passes; and
write only normal planner outputs in the existing candidate. It may not make any S3 or other
network request, GET a raw ZIP, invoke acquisition, use Coinalyze, edit generation 0, select a
subset, clean/delete/replace the candidate, patch source/tests, or transition generations. The
checkpoint and physical page-set identities must remain unchanged; any change is unsafe and is
recorded without another invocation.

Hermes must launch the planner exactly once inside a detached shell wrapper using `setsid` and
`nohup`, with an outer four-hour `timeout`. The wrapper must use a fresh `mktemp -d` directory
under `/tmp`, redirect the planner's exact stdout and stderr to separate files there, and write
start UTC, end UTC, and the wrapper/timeout exit code to an atomically renamed result file. The
launcher must record the wrapper PID and Linux process-start ticks. The wrapper and its output
files are execution instrumentation only; they may not alter the planner command, repository,
candidate, or active generation.

Hermes must poll that exact PID/start-tick identity and result file. A later harness call may
continue polling the same wrapper, but no call may launch a second planner. An exit code, timeout,
missing result after process disappearance, or other abnormal condition all end this assignment.
The runner directory must remain present through record publication; no cleanup is authorized.

## Mandatory record 384 and stop

Hermes must publish exactly
`research/sprint_004/384_CEX002_OFFLINE_CAPTURED_CONTINUATION_RECORD.md` after the one terminal
result. It must contain:

- exact preflight identities and the four corrected code-hash fields;
- runner directory, wrapper PID/start ticks, exact planner command, timestamps, timeout, exit
  code, complete stdout/stderr, and hashes/byte counts of all runner evidence files;
- exact unchanged before/after checkpoint and physical page-set identities and per-pass facts;
- exact resulting manifest/receipt/lineage/locator facts when present, or exact blocked/unsafe/
  abnormal facts when absent;
- all semantic/count/byte/capacity/code/generation facts required by Review 379 for a completed
  candidate; and
- an explicit statement that execution accepts no revision and authorizes no acquisition or
  transition.

Before repository control, Hermes must set both literal top-level actor fields to the reviewer,
update both summaries with the exact outcome, keep CEX-002 and Gate 2 `IN_PROGRESS`, and keep next
ticket `NONE`. It then runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/384_CEX002_OFFLINE_CAPTURED_CONTINUATION_RECORD.md tickets/CEX-002.md
```

Record 384 must contain the exact outputs and exit codes with Hermes attribution. Hermes stages
exactly those three paths, verifies no other staged path, commits, pushes main, proves
`HEAD == origin/main`, and stops. Candidate and runner data remain unstaged. Harness output is a
handoff aid only; repository evidence is authoritative.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/383_CEX002_RECORD382_HASH_REJECTION_AND_OFFLINE_CAPTURE_RETRY_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No developer source/test, implementation evidence, candidate data, acceptance command, or
unrelated dirty path is included.
