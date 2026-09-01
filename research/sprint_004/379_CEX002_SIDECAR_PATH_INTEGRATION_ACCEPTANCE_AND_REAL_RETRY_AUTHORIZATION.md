# CEX-002 Sidecar-Path Integration Acceptance and Real Retry Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** sidecar-path integration/evidence accepted; one corrected listing-only candidate retry authorized
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Integration and evidence acceptance

The reviewer accepts the Review-373 sidecar-path integration and its combined repository-native
evidence:

- integration commit `291d066322cc3368c34552a6f5257ee4059cd8f6` contains exactly the two
  accepted developer paths, record 374, and two control-plane paths;
- source SHA-256 is
  `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b` at 5,096 lines;
- test SHA-256 is
  `aa4a09b4c8bee732515961c09ac890ef83f69be6395dd9c3770c4383ee05b149` at 2,646 lines;
- record 374 contains the exact targeted pytest and ruff commands and complete zero results:
  123 cases passed with no warnings and ruff reported `All checks passed!`;
- record 376 contains the exact repository-control and scoped-diff commands, zero exit codes,
  `Repo control check: PASS`, and the required empty streams;
- record 378 correctly identifies Hermes as record 376's executing/publication actor without
  rewriting the historical record and documents a fresh zero repository-control/scoped-diff
  pair against the correction paths;
- `HEAD == origin/main == f4b76d55bfc33cd0c79efebd617080f77bcc3b92`, staging is empty, developer
  hashes are unchanged, and unrelated dirty work remains present and unstaged.

One final governance defect is disclosed. Record 378 says both top-level actor fields name the
reviewer, but the ticket header retained Hermes's completed Review-377 assignment; only
`CURRENT_TASK.md` named the reviewer. This does not invalidate the exact implementation or
command evidence. This review supersedes that stale ticket assignment with Hermes's new,
distinct real-run assignment. After the run, Review 379 requires literal final reviewer fields
before repository control.

This accepts corrected implementation integration only. It does not yet accept a candidate or
pass Gate 2.

## Exact real-run authorization

Read-only inspection confirms that
`data/cex002_qualify/gate2_revision_candidate` remains absent. Hermes is authorized for exactly
one invocation:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before invoking, Hermes must read `AGENTS.md`, the current task, CEX-002, ADR-0031, records
371-379, prove `HEAD == origin/main` at this review's publication commit, prove empty staging and
absent candidate locator, and rehash the integrated production, CLI, and test paths. A mismatch
stops before the real command and is still recorded.

The invocation may acquire only the accepted nonblocking locks; query-only authenticate the real
generation-0 SQLite/WAL/SHM, code, retained sidecars, and content roots; make only fixed official
Binance S3 HTTPS ListObjectsV2 requests for the two affected prefixes in two independent passes;
and create/resume only the fixed sibling candidate checkpoint/pages/tmp/manifest/receipt/lineage/
locator tree.

It may not GET a raw ZIP, use a Coinalyze secret, edit active generation 0, follow redirects,
select a family/symbol/key/date subset, clean or replace a candidate, invoke the old acquisition,
or start a generation transition.

The command is authorized once only. Exit 0, 2, 1, 6, or abnormal failure all end the invocation.
Hermes must not rerun, resume, repair, delete, clean, or patch anything during this assignment.

## Mandatory record 380

Regardless of outcome, Hermes must publish exactly
`research/sprint_004/380_CEX002_SIDECAR_CORRECTED_REVISION_CANDIDATE_RUN_RECORD.md`. It must name
Jr Dev - Hermes through the installed harness as executing actor and contain:

- exact start/end UTC timestamps, command, exit code, stop reason, stdout, and stderr;
- pre-run HEAD/origin and production/CLI/test hashes;
- confirmation that the command ran once and no raw/acquisition command ran;
- candidate checkpoint/locator presence and bounded SHA-256/byte identities for every published
  locator-referenced manifest, receipt, and lineage asset;
- for a complete result, the exact semantic identity, pending/family/message/classification
  counts, old/current/delta byte equations, maximum object bytes, two pass/page counts and stable
  graph/pending hashes, manifest row/byte/hash facts, capacity projection, code/generation state
  identities, false authorization booleans, and proof that every retained request URL is the
  fixed listing endpoint rather than a raw object URL;
- for a partial result, exact checkpoint identity and per-pass durable progress;
- for a blocked/unsafe/abnormal result, the exact refusal and whether a locator exists; and
- an explicit statement that the result accepts no revision and authorizes no acquisition.

Hermes may use bounded read-only stat/hash/JSON inspection of planner-produced candidate files but
may not directly query active real SQLite/data outside the one integrated planner invocation.

Before repository control, Hermes must create final record 380 and set these literal lines:

```text
Next required actor: Lead Quantitative Finance Researcher/Engineer
**Next required actor:** Lead Quantitative Finance Researcher/Engineer
```

The first belongs in `CURRENT_TASK.md`; the second belongs in CEX-002. Both summaries must report
the exact run outcome, keep CEX-002 and Gate 2 `IN_PROGRESS`, keep next ticket `NONE`, and prohibit
all retry/resume/acquisition/transition/later work. Only after those final bytes exist, Hermes
runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/380_CEX002_SIDECAR_CORRECTED_REVISION_CANDIDATE_RUN_RECORD.md tickets/CEX-002.md
```

Record 380 must contain those commands' exact outputs/exit codes and correctly attribute Hermes.
Hermes stages exactly record 380 plus the two control-plane paths, verifies no other staged path,
commits, pushes, proves `HEAD == origin/main`, and stops. Candidate data is never staged. Every
unrelated dirty path remains present and unstaged. Harness output is a handoff aid only.

No raw acquisition, generation transition, Gate 3, model work, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/379_CEX002_SIDECAR_PATH_INTEGRATION_ACCEPTANCE_AND_REAL_RETRY_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

Real state/data, candidate execution evidence, and every unrelated dirty path are excluded from
this reviewer publication.
