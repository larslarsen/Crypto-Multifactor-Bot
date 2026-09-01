# CEX-002 Payload-Schema Integration Acceptance and Real Retry Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** payload-schema integration accepted; one corrected listing-only candidate retry authorized
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Integration acceptance

The reviewer independently inspected Hermes commit
`ad081ac4a5a999bb538ce8ba81c948c85712ebfd` and accepts the payload-schema integration:

- `HEAD == origin/main` at that commit;
- the commit contains exactly the two accepted developer paths, record 369, `CURRENT_TASK.md`,
  and `tickets/CEX-002.md`;
- source SHA-256 is
  `06d43d085e3d38d8af9043ebc6a5353c8d7de8bf9bd9cde0ac6e3e94b9e6e553` at 5,095 lines;
- test SHA-256 is
  `e708e7ac9ddf183fd2702cfca97677a5dc761966819f9f1aedecb81106704630` at 2,593 lines;
- record 369 contains the exact four commands and their zero results: 119 targeted cases passed,
  ruff reported `All checks passed!`, repository control reported `PASS`, and the scoped diff
  check was empty;
- the staging area is empty; and
- every unrelated dirty path remains present and unstaged.

One governance defect is disclosed. Record 369 says the final control-plane update named the
reviewer in both actor fields, but `CURRENT_TASK.md` retained the completed Hermes integration
assignment while the ticket correctly named the reviewer. The mandated repository-control
command also preceded final record/control-plane publication, so its green result cannot prove
those final fields. This does not invalidate the source/test commands or exact integration. This
review supersedes the stale assignment with Hermes's new, distinct execution assignment. For the
run below, final record and actor fields must exist before repository control is invoked.

This accepts corrected implementation integration only. It does not yet accept a real candidate
or pass Gate 2.

## Exact corrected real-run authorization

Read-only inspection confirms that the fixed candidate locator
`data/cex002_qualify/gate2_revision_candidate` is absent. Hermes is authorized for exactly one
invocation:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before invoking, Hermes must read `AGENTS.md`, the current task, CEX-002, ADR-0031, records
366-370, prove `HEAD == origin/main` at this review's publication commit, prove empty staging,
and rehash the integrated production, CLI, and focused test paths. A mismatch stops before the
real command and is still recorded.

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

The command is authorized once only. Exit 0 (`complete`), 2 (`resumable_partial`), 1 (`blocked`),
6 (`unsafe`), or an abnormal failure all end the invocation. Hermes must not rerun, resume,
repair, delete, clean, or patch anything during this assignment.

## Mandatory durable record

Regardless of outcome, Hermes must publish exactly
`research/sprint_004/371_CEX002_CORRECTED_REVISION_CANDIDATE_RUN_RECORD.md`. The record is
execution evidence, not acceptance, and must contain:

- exact start/end UTC timestamps, command, exit code, stop reason, stdout, and stderr;
- pre-run HEAD/origin and production/CLI/test hashes;
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
to construct this evidence. It may not directly inspect or query active real SQLite/data outside
the one integrated planner invocation.

Hermes must create record 371 and update `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`
before running repository control. Both final top-level actor fields must name the reviewer,
CEX-002 and Gate 2 remain `IN_PROGRESS`, next ticket remains `NONE`, and all retry/resume/
acquisition/transition/later work remains unauthorized. Only after those final fields and record
exist, Hermes runs:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/371_CEX002_CORRECTED_REVISION_CANDIDATE_RUN_RECORD.md tickets/CEX-002.md
```

Hermes stages exactly record 371, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other
path is staged; commits; pushes `main`; proves `HEAD == origin/main`; and stops. Candidate data is
not staged or committed. Harness output is a handoff aid only; all execution evidence and state
must be repository-native. Every unrelated dirty path remains present and unstaged.

No model work, Gate 3, next ticket, raw acquisition, or generation transition is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/370_CEX002_PAYLOAD_SCHEMA_INTEGRATION_ACCEPTANCE_AND_REAL_RETRY_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

Real state/data, candidate execution evidence, and every unrelated dirty path are excluded from
this reviewer publication.
