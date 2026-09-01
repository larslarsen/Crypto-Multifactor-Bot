# CEX-002 Record-392 Acceptance and V2 Continuation Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept evidence/control-plane completion with one corrected hash; authorize one v2 continuation
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Evidence acceptance and correction

The reviewer accepts Hermes commit `d12f9899ccaf14bfb77b17ec17d5d9c860dc81d7` as the
Review-391 evidence/control-plane completion:

- the commit contains exactly record 392, `docs/handoff/CURRENT_TASK.md`, and
  `tickets/CEX-002.md`;
- record 390 is unchanged;
- both summaries report the exact exit-2 partial result and both top-level actor fields name the
  reviewer before publication;
- record 392 contains the exact fresh repository-control PASS and empty scoped-diff results with
  zero exit codes and Hermes attribution;
- `HEAD == origin/main == d12f9899ccaf14bfb77b17ec17d5d9c860dc81d7`, staging is empty, and
  all unrelated dirty paths remain unstaged; and
- no planner, network, v1/v2 mutation, SQLite query, source/test edit, acquisition, cleanup, or
  transition occurred during the correction.

One runner-table value is rejected and superseded. Record 392 transcribes `exit_code.txt` SHA-256
as `53c234e5e472...`; independent rehashing proves the exact value is
`53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3`. The file is two bytes and
contains exit code `2`. This clerical error does not change the captured terminal result or the
other six accepted runner identities.

The partial candidate remains unchanged after publication: checkpoint SHA-256
`aaaaf68a0f0f132d086140f66f6526905f70eaf5c2cc31c35c51431e3ffc6748`, 1,838 page files,
pass 1 at 1,164/1,308 completed/discovered prefixes and 1,838 pages, pass 2 at zero pages, and no
manifest, receipt, lineage, or locator. V1 and the three integrated code hashes remain exact. No
planner process is live.

Record 390 plus Reviews 391-393 and record 392 now form the durable authority for the fresh-run
and publication history. No ephemeral harness statement is relied upon as a decision.

## One exact continuation authorized

The accepted implementation authenticates the existing v2 checkpoint/pages, reconstructs its
graphs and private listing index, and continues only missing requests. The transient exit is an
ordinary resumable condition. Hermes is authorized for exactly one continuation invocation:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before launch, Hermes must read `AGENTS.md`, the current task, full CEX-002 ticket, ADR-0032, and
Reviews/records 389-393; prove `HEAD == origin/main` at this review's publication commit; prove
staging empty and no planner process live; rehash production, test, and CLI; reprove the exact v2
checkpoint/page count/no-locator facts and unchanged v1 hashes above. Any mismatch stops before
launch and is recorded.

The command may query-only authenticate generation 0; authenticate and resume only the existing
v2 checkpoint/pages/private index; issue only missing official Binance S3 ListObjectsV2 requests
for the same two fixed family roots and independent passes; and publish only normal v2 candidate
outputs. It may not GET a raw ZIP, use Coinalyze, edit generation 0, reference or mutate v1,
select a subset, delete/clean/replace v2, invoke old acquisition, patch source/tests, transition
generations, or start later work.

The command is authorized once in one durable runner with a wall-clock allowance of at least four
hours. Before detaching, Hermes must atomically retain the runner/timeout PID and Linux start ticks;
if the Python planner PID is distinct, it must retain that PID and start ticks too. The runner must
separately retain start/end UTC, stdout, stderr, exit code, and an atomically completed status/result
file. A later Hermes harness may poll only those exact PID/start-tick identities and the same runner
files if the first harness returns while the process remains live. It must not relaunch, replace,
resume a second time, truncate runner streams, or reuse the prior runner directory.

Exit 0, 1, 2, 6, 124, another nonzero, process disappearance, or abnormal capture consumes the
single continuation. No second continuation is authorized by this review. Based on retained work,
the expected runtime is roughly 60 to 100 minutes, but the four-hour ceiling governs.

## Mandatory record 394 and stop

Every terminal outcome must be published as
`research/sprint_004/394_CEX002_V2_REVISION_CANDIDATE_CONTINUATION_RECORD.md`. It must contain:

- exact preflight Git/code/v1/v2/process facts;
- fresh runner directory, exact PID/start-tick identities, exact command, timestamps, allowance,
  exit code/stop reason, complete separate streams, and every runner-file byte/hash identity;
- exact before/after v2 checkpoint and page inventory plus per-pass progress;
- proof of one continuation and no prohibited action;
- for completion, every locator/receipt/manifest/lineage, semantic, pending/count/classification,
  byte/capacity, listing-stability, code/generation, and false-authorization fact required by
  Review 389; or the exact partial/blocked/unsafe/abnormal facts when not complete; and
- an explicit statement that the outcome accepts no candidate and authorizes no acquisition or
  transition.

Hermes may use bounded read-only stat/hash/JSON inspection of v2 outputs after termination but may
not directly query active or candidate real SQLite outside the planner invocation.

Before repository control, Hermes must set these literal final fields:

```text
Next required actor: Lead Quantitative Finance Researcher/Engineer
**Next required actor:** Lead Quantitative Finance Researcher/Engineer
```

Both summaries must replace the completed continuation assignment with the exact outcome, keep
CEX-002 and Gate 2 `IN_PROGRESS`, keep next ticket `NONE`, and prohibit every further
resume/acquisition/transition/later action. Hermes then runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/394_CEX002_V2_REVISION_CANDIDATE_CONTINUATION_RECORD.md tickets/CEX-002.md
```

Record 394 must contain those exact outputs and exit codes. If both pass, Hermes stages exactly
record 394 and the two control-plane paths, verifies no other staged path, commits, pushes `main`,
proves `HEAD == origin/main`, and stops. Candidate/runner data and all unrelated dirty paths remain
unstaged. Harness output is a handoff only; a later reviewer record alone accepts or rejects the
candidate.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/393_CEX002_RECORD392_ACCEPTANCE_AND_V2_CONTINUATION_AUTHORIZATION.md`; and
- `tickets/CEX-002.md`.

No candidate/runner data, source/test, implementation evidence, acceptance command, or unrelated
dirty path is included in this reviewer publication.
