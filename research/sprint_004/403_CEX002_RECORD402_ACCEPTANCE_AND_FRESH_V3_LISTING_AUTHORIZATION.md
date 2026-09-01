# CEX-002 Record-402 Acceptance and Fresh V3 Listing Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept record 402 and integrated v3 authority; authorize one fresh v3 listing-only invocation
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Record-402 acceptance

The reviewer accepts Hermes evidence commit
`ca33da91e1e1d391a99a067fe86b828f0e08a078` as the exact three-path Review-401 completion:

- its parent is Review-401 publication commit
  `d3a947d449479a52107ac7f85e89d791e5d4f5a5` and it contains exactly record 402 plus the two
  control-plane paths;
- record 400 is preserved unchanged;
- the corrected integration preflight is exact: 13 total modified paths consisted of the two
  accepted developer paths plus 11 unrelated modified paths, alongside 13 unrelated untracked
  paths;
- no separate `--collect-only` command ran; the standard authorized pytest command's own
  `147 passed in 39.87s` summary supplied the correct case count, and record 400 falsely
  attributed that count to a collection invocation;
- no reconstruction/rerun or source/test/data action occurred during the correction;
- both publication checks exited 0, staging is empty, and
  `HEAD == origin/main == ca33da91e1e1d391a99a067fe86b828f0e08a078`; and
- both top-level actor fields name the reviewer.

Review 401's exact five-path v3 implementation integration remains accepted. No v3 candidate,
manifest, receipt, lineage, locator, raw acquisition, Gate-2 result, generation transition, later
gate, or later ticket is accepted by either record.

## Reviewer preflight facts

Bounded read-only inspection establishes:

- no revision-candidate planner process is live;
- `data/cex002_qualify/gate2_revision_candidate_v3` is absent;
- integrated source SHA-256 is
  `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32`;
- integrated test SHA-256 is
  `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905`;
- planner CLI SHA-256 is
  `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`;
- acquisition source/CLI SHA-256 values are respectively
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` and
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- the immutable v1 checkpoint/private-index SHA-256 values remain respectively
  `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` and
  `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`; and
- the immutable v2 checkpoint/private-index SHA-256 values remain respectively
  `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` and
  `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a`.

The reviewer opened no candidate SQLite database and mutated no data. V1 and v2 remain immutable
blocked evidence and are not inputs to v3.

## One exact fresh v3 invocation

Hermes is authorized for exactly one invocation of the integrated listing-only planner:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before launch, Hermes must read `AGENTS.md`, the current task, full CEX-002 ticket, ADR-0033, and
Reviews 399-403; prove `HEAD == origin/main` at this review's publication commit; prove staging
empty and no revision-candidate planner process live; rehash all five code paths and all four
v1/v2 checkpoint/private-index identities above; and prove the fixed v3 root is absent. It may
hash but may not open either blocked candidate's SQLite database. Any mismatch stops before launch
and is recorded without creating v3.

The invocation may acquire only the planner's accepted nonblocking locks; query-only authenticate
generation 0; issue only fixed official Binance S3 HTTPS ListObjectsV2 requests for the two
affected family roots in two independent passes; and create only the fresh fixed v3 checkpoint,
pages, private index, manifest, receipt, lineage, and locator tree. It may authenticate retained
generation-0 sidecars/content through the accepted held descriptors.

It may not reference or mutate v1/v2; GET a raw ZIP; use Coinalyze; edit generation 0; follow
redirects; select a family/symbol/key/date subset; invoke acquisition; clean or replace anything;
patch source/tests; transition generations; or start later work.

Hermes must launch the planner once in one long-lived execution session with a wall-clock allowance
of at least four hours. If the command tool returns a live session identifier, Hermes must poll
only that same session until it terminates. If tool attachment is lost, Hermes may use the original
PID and Linux start ticks only to observe that same process; it must never launch a replacement or
duplicate. Exit 0, 1, 2, 6, 124, any other nonzero exit, process disappearance, power loss, or
external interruption consumes the single invocation and ends execution. No rerun, resume, repair,
cleanup, or second invocation is authorized in this assignment.

Before launch, Hermes must create a fresh `mktemp -d` runner under `/tmp` and durably capture
separate stdout/stderr, start/end UTC, exit code, shell PID/start ticks, planner PID/start ticks,
the exact runner script, and terminal status for that one process. Runner files are instrumentation
only and may not alter the planner command, repository, candidate, or generation. The runner must
remain present through record publication; no cleanup is authorized.

## Mandatory record 404 and stop

After the single invocation reaches any terminal result, Hermes must publish exactly
`research/sprint_004/404_CEX002_FRESH_V3_REVISION_CANDIDATE_RUN_RECORD.md`. It must identify Jr
Dev - Hermes as executing actor and contain:

- exact preflight HEAD/origin, staging, process, code hashes, absent-v3, and unchanged-v1/v2 facts;
- runner directory and exact hashes/bytes for every runner file, exact command, shell and planner
  PID/start ticks, start/end UTC, elapsed time, wall allowance, exit code, stop reason, and complete
  separate stdout/stderr;
- proof the planner ran exactly once and no prohibited raw/acquisition/v1/v2 action occurred;
- for a partial result, exact v3 checkpoint identity, page inventory, per-pass prefix/page progress,
  cursor, and absent locator/publication facts;
- for blocked, unsafe, timeout, or abnormal termination, the exact refusal, v3 checkpoint/page
  state, and whether any locator/publication asset exists;
- for completion, exact locator/receipt/manifest/lineage identities, semantic identity,
  pending/family/classification/message counts, old/current/delta byte equations, maximum object,
  stable reachability and pending hashes, pass/page/prefix counts, capacity projection,
  code/generation identities, and all false authorization booleans; and
- an explicit statement that the outcome accepts no candidate and authorizes no acquisition or
  transition.

After the process terminates, Hermes may use bounded read-only stat/hash/JSON inspection of
planner-produced v3 files and runner files. It may not directly query any real SQLite database
outside the single integrated planner invocation.

Before repository control, Hermes must set these literal final fields:

```text
Next required actor: Lead Quantitative Finance Researcher/Engineer
**Next required actor:** Lead Quantitative Finance Researcher/Engineer
```

Both summaries must state the exact terminal outcome, keep CEX-002 and Gate 2 `IN_PROGRESS`, keep
next ticket `NONE`, and prohibit every retry/resume/acquisition/transition/later action. Only after
those final bytes exist, Hermes runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/404_CEX002_FRESH_V3_REVISION_CANDIDATE_RUN_RECORD.md tickets/CEX-002.md
```

Record 404 must contain both commands' exact outputs and exit codes with Hermes attribution.
Hermes stages exactly record 404 and the two control-plane paths, verifies no other staged path,
commits, pushes `main`, proves `HEAD == origin/main`, and stops. Candidate and runner bytes are
never staged. Every unrelated dirty path remains present and unstaged. Harness output is a handoff
aid only; record 404 is the execution evidence and only a later reviewer record may accept or
reject the candidate.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/403_CEX002_RECORD402_ACCEPTANCE_AND_FRESH_V3_LISTING_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No candidate/runner data, developer source/test, implementation evidence, acceptance command, or
unrelated dirty path is included in this reviewer publication.
