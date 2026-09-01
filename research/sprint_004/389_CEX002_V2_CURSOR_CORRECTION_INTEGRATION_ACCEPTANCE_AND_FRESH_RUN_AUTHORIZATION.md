# CEX-002 V2 Cursor Correction Integration Acceptance and Fresh Run Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept Review-387 integration; correct record-388 summaries; authorize one fresh v2 listing-only run
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Integration acceptance

The reviewer accepts Hermes integration commit
`9eb6b39c1a61d989a78f262fa91715329715ce8a` and record 388 on this exact basis:

- the commit has parent `52dc71402900209da27a3f75d1db69ad9fa5d13f` and contains exactly the two
  Review-387 developer paths, record 388, `docs/handoff/CURRENT_TASK.md`, and
  `tickets/CEX-002.md`;
- production SHA-256 remains
  `2f7ebacaba729c57896de7489646d517bd481347534340f3c452a7a394e76309` at 5,150
  lines;
- test SHA-256 remains
  `090fa536c21213767c467533827c900d0c60c182ab1fd3f283316a033449337f` at 3,140
  lines and 68 test functions;
- the exact Review-387 targeted pytest exited 0 with all 139 cases passing in 53.00 seconds;
- targeted ruff exited 0 with `All checks passed!`;
- repository control exited 0 with `Repo control check: PASS`;
- the final five-path scoped diff check exited 0 with empty output;
- `HEAD == origin/main == 9eb6b39c1a61d989a78f262fa91715329715ce8a`, staging is empty, and the
  unrelated dirty paths remain unstaged; and
- both top-level actor fields name the reviewer after integration.

Two record/control-plane descriptions are corrected without rewriting record 388. Its preflight
calls all 13 modified paths unrelated; exactly 11 were unrelated, while the other two were the
authorized developer drop. All 11 unrelated modified and 13 unrelated untracked paths remain
present after integration. Also, the final `CURRENT_TASK.md` and ticket summaries retain the
completed Hermes integration assignment as future work. This review supersedes that stale prose.
Neither reporting defect changes the exact commit scope, developer identities, validation
results, or integration acceptance.

This accepts implementation integration only. It does not accept a v2 candidate, authorize raw
acquisition, pass Gate 2, or authorize a later gate or ticket.

## Candidate preflight authority

Bounded reviewer inspection after integration confirms:

- the new fixed `data/cex002_qualify/gate2_revision_candidate_v2` root is absent;
- the blocked v1 root remains the only `gate2_revision_candidate*` sibling;
- v1 checkpoint SHA-256 remains
  `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`; and
- v1 private-index SHA-256 remains
  `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`.

The v1 tree remains immutable evidence and is not an input to v2. No v1 delete, rename, copy,
hard-link, import, relabel, cleanup, or repair is authorized.

## One exact fresh v2 invocation

Hermes is authorized for exactly one invocation of the integrated listing-only planner:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before launch, Hermes must read `AGENTS.md`, the current task, full CEX-002 ticket, ADR-0032, and
Reviews 386-389; prove `HEAD == origin/main` at this review's publication commit; prove staging
empty and no revision-candidate planner process live; rehash the exact production, test, and CLI
paths; prove the v2 root is absent; and reprove the two v1 identities above without opening v1
SQLite. Any mismatch stops before launch and is recorded.

The invocation may acquire only the planner's accepted nonblocking locks; query-only authenticate
generation 0; issue only fixed official Binance S3 HTTPS ListObjectsV2 requests for the two
affected family roots in two independent passes; and create only the fresh fixed v2 checkpoint,
pages, private index, manifest, receipt, lineage, and locator tree. It may authenticate retained
generation-0 sidecars/content through the accepted held descriptors.

It may not reference or mutate v1; GET a raw ZIP; use Coinalyze; edit generation 0; follow
redirects; select a family/symbol/key/date subset; invoke the old acquisition; clean or replace
anything; patch source/tests; transition generations; or start later work.

Hermes must launch the planner once in one long-lived execution session with a wall-clock
allowance of at least four hours. If the command tool returns a live session identifier, Hermes
must poll only that same session until it terminates. If tool attachment is lost, Hermes may use
the original PID and Linux start ticks only to observe that same process; it must never launch a
replacement or duplicate. Exit 0, 1, 2, 6, 124, another nonzero exit, process disappearance, or
external interruption all consume the single invocation and end the execution phase. No rerun,
resume, repair, cleanup, or second invocation is authorized in this assignment.

Before launch, Hermes must create a fresh `mktemp -d` runner directory under `/tmp` and arrange
durable, separate stdout/stderr, start/end UTC, exit-code, PID, and Linux-start-tick capture for
that one process. Runner files are instrumentation only and may not alter the planner command,
repository, candidate, or generation. The runner directory must remain present through record
publication; no cleanup is authorized.

## Mandatory record 390 and stop

After the single invocation reaches its terminal result, Hermes must publish exactly
`research/sprint_004/390_CEX002_FRESH_V2_REVISION_CANDIDATE_RUN_RECORD.md`. It must identify Jr
Dev - Hermes as executing actor and contain:

- exact preflight HEAD/origin, staging, process, source/test/CLI hashes, absent-v2, and unchanged-v1
  facts;
- runner directory, exact command, PID/start ticks, start/end UTC, wall-clock allowance, exit
  code, stop reason, and complete separate stdout/stderr;
- proof the planner ran exactly once and no prohibited raw/acquisition/v1 action occurred;
- for a partial result, exact v2 checkpoint identity, page inventory, and per-pass progress;
- for blocked, unsafe, timeout, or abnormal termination, the exact refusal and whether a v2
  locator exists;
- for completion, exact locator/receipt/manifest/lineage identities, semantic identity,
  pending/family/classification/message counts, old/current/delta byte equations, maximum object,
  stable graph/pending hashes, pass/page/prefix counts, capacity projection, code/generation
  identities, and false authorization booleans; and
- an explicit statement that the outcome accepts no candidate and authorizes no acquisition or
  transition.

Hermes may use bounded read-only stat/hash/JSON inspection of planner-produced v2 files after the
process terminates. It may not directly query active or candidate real SQLite outside the one
integrated planner invocation.

Before repository control, Hermes must set these literal final fields:

```text
Next required actor: Lead Quantitative Finance Researcher/Engineer
**Next required actor:** Lead Quantitative Finance Researcher/Engineer
```

Both summaries must state the exact terminal outcome, keep CEX-002 and Gate 2 `IN_PROGRESS`, keep
next ticket `NONE`, and prohibit every retry/resume/acquisition/transition/later action. Only
after those final bytes exist, Hermes runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/390_CEX002_FRESH_V2_REVISION_CANDIDATE_RUN_RECORD.md tickets/CEX-002.md
```

Record 390 must contain both commands' exact outputs and exit codes with Hermes attribution.
Hermes stages exactly record 390 and the two control-plane paths, verifies no other staged path,
commits, pushes `main`, proves `HEAD == origin/main`, and stops. Candidate and runner data are
never staged. Every unrelated dirty path remains present and unstaged. Harness output is a
handoff aid only; record 390 is the execution evidence and only a later reviewer record may
accept or reject the candidate.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/389_CEX002_V2_CURSOR_CORRECTION_INTEGRATION_ACCEPTANCE_AND_FRESH_RUN_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No candidate/runner data, developer source/test, implementation evidence, acceptance command, or
unrelated dirty path is included in this reviewer publication.
