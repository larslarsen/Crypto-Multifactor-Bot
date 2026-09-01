# CEX-002 Revision-Candidate Integration Acceptance and Run Authorization

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** integration accepted; one real listing-only candidate invocation authorized
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Integration acceptance

The reviewer independently inspected Hermes commit
`aa365747df0b799be0fa2bf039dc522a693c3ffa` and accepts the implementation integration:

- `HEAD == origin/main == aa365747df0b799be0fa2bf039dc522a693c3ffa`;
- the commit contains exactly nine authorized paths: six accepted developer paths, record 364,
  `CURRENT_TASK.md`, and `tickets/CEX-002.md`;
- all six installed SHA-256 identities exactly match Review 363;
- record 364 durably contains the exact four commands, complete outputs, and exit codes;
- targeted pytest passed 109 cases with no warnings;
- targeted ruff reported `All checks passed!`;
- repository control reported `PASS`;
- scoped diff check was empty;
- the staging area is empty; and
- every unrelated dirty path remains present and unstaged.

One governance defect is disclosed and corrected here. Record 364 says the ticket was updated
exactly, but its top-level `Next required actor` remained the completed Review-363 integration
assignment. The command result is not invalidated, but record 364 overstates the final control-
plane update and its repository-control `PASS` preceded that stale final state. Under the narrow
reviewer-publication exception, this review corrects the ticket header while publishing the next
decision. The reviewer does not edit record 364 or rerun its command.

This accepts implementation integration only. It does not yet accept a real candidate or pass
Gate 2.

## Exact real-run authorization

ADR-0031 requires one separate listing-only revision candidate before any replacement source,
state transition, or raw acquisition. Jr Dev - Hermes is authorized for exactly one invocation:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

The invocation may:

- acquire the accepted nonblocking acquisition and candidate locks;
- read and authenticate the real generation-0 SQLite/WAL/SHM, code, retained sidecars, and
  content roots through the integrated planner's bounded no-follow/query-only path;
- make only the planner-enforced HTTPS ListObjectsV2 requests to the fixed official Binance S3
  listing endpoint for the two affected prefixes and perform two independent passes; and
- create or resume only the fixed sibling
  `data/cex002_qualify/gate2_revision_candidate` checkpoint/pages/tmp/manifest/receipt/lineage/
  locator tree.

It may not GET a raw ZIP, use a Coinalyze secret, edit the active generation, follow redirects,
select a family/symbol/key/date subset, clean or replace an existing candidate, invoke the old
acquisition, or start a generation transition.

Before invoking, Hermes must read AGENTS, the current task, CEX-002, ADR-0031, records 364 and
this review; prove `HEAD == origin/main` at this review's publication commit; and rehash the
installed production/CLI identities. A mismatch stops before the real command and is still
recorded.

The real command is authorized once only. Exit 0 (`complete`), 2 (`resumable_partial`), 1
(`blocked`), 6 (`unsafe`), or an abnormal failure all end the invocation. Hermes must not rerun,
resume, repair, delete, clean, or patch anything during this assignment.

## Mandatory durable record

Regardless of outcome, Hermes must publish exactly
`research/sprint_004/366_CEX002_REVISION_CANDIDATE_RUN_RECORD.md`. The record is execution evidence,
not acceptance, and must contain:

- exact start/end UTC timestamps, command, exit code, stop reason, stdout, and stderr;
- pre-run HEAD/origin and source/CLI hashes;
- confirmation that the command ran once and no raw/acquisition command ran;
- candidate checkpoint/locator presence and safe read-only SHA-256/byte identities for every
  published locator-referenced manifest, receipt, and lineage asset;
- for a complete result, the exact semantic identity, pending/family/message/classification
  counts, old/current/delta byte equations, maximum object bytes, two pass/page counts and stable
  graph/pending hashes, manifest row/byte/hash facts, capacity projection, code/generation state
  identities, false authorization booleans, and evidence that every retained request URL is the
  fixed listing endpoint rather than a raw object URL;
- for a partial result, exact checkpoint identity and per-pass durable progress;
- for a blocked/unsafe/abnormal result, the exact refusal and whether a locator exists; and
- an explicit statement that no candidate result accepts a revision or authorizes acquisition.

Hermes may use bounded read-only stat/hash/JSON inspection of the planner-produced candidate tree
to construct this evidence. It may not directly inspect or query the active real SQLite/data
outside the one integrated planner invocation.

Hermes updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002
`IN_PROGRESS`, name the reviewer as next actor in both top-level actor fields, keep next ticket
`NONE`, report the exact run outcome, and state that all retry/resume/acquisition/transition/later
work remains unauthorized. It runs `python3 scripts/check_repo_control.py` only after those final
top-level fields and record 366 exist, then runs a diff check scoped to record 366 and the two
control-plane paths.

Hermes stages exactly record 366, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other
path is staged; commits; pushes `main`; proves `HEAD == origin/main`; and stops. Candidate data is
not staged or committed. Harness output is a handoff aid only; all execution evidence and state
must be repository-native.

No model work, Gate 3, next ticket, or acquisition is authorized. Gate 2 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/365_CEX002_REVISION_CANDIDATE_INTEGRATION_ACCEPTANCE_AND_RUN_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

Real state/data, candidate execution evidence, and every unrelated dirty path are excluded from
this reviewer publication.
