# CEX-002 Integration Evidence Attribution and Control-Plane Stop

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** command evidence accepted; executing-actor attribution and final summaries rejected
- **Corrective actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reviewer disposition

The reviewer independently inspected commit
`6337bedf626a8ec2cbe1d66fbb7693fecae7d3d8`, record 376, both control-plane paths, the exact
three-path commit, matching remote, empty staging, unchanged developer hashes, and preserved
unrelated dirty paths.

Record 376 durably supplies the evidence missing from record 374. It gives the exact two commands,
exit 0 for both, stdout `Repo control check: PASS` and empty stderr for repository control, and
empty stdout/stderr for scoped diff. Those command results are accepted.

The publication is not yet acceptable as the final control-plane state:

1. record 376 incorrectly says its executing actor was the Lead Quantitative Finance
   Researcher/Engineer, although Hermes executed the commands and authored/committed/pushed the
   record under Review 375; and
2. `CURRENT_TASK.md` and the ticket still describe record 374 evidence as incomplete and do not
   identify record 376 as its completion.

The Git history remains the transparent authority for the incorrect record. Record 376 must not
be rewritten. A new append-only correction must identify the actual actor and supersede only the
incorrect attribution/final summaries. The accepted command facts and developer bytes remain
unchanged.

No real retry, candidate acceptance, or Gate-2 acceptance is authorized.

## Exact Hermes correction

Hermes is authorized only to create
`research/sprint_004/378_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_CORRECTION.md`
and update `CURRENT_TASK.md` and CEX-002. Record 378 must:

- identify Jr Dev - Hermes through the installed one-shot harness as record 376's actual
  executing/publication actor;
- preserve and cite record 376's accepted exact commands, streams, and exit codes without
  claiming a rerun;
- state that record 376's reviewer attribution is superseded but the historical file is not
  rewritten;
- state that the combined records 374, 376, and 378 complete Review 373's integration evidence;
- retain the exact installed developer hashes and `HEAD == origin/main` precondition; and
- state that no source/test edit, pytest, lint, planner, network/data, or later work occurred.

Hermes must update both control-plane summaries to say integration evidence is complete and name
the reviewer as next actor before running commands. It then runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/378_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_CORRECTION.md tickets/CEX-002.md
```

The correction may be committed only if repository control exits 0 with exact stdout
`Repo control check: PASS` and empty stderr, and scoped diff exits 0 with empty stdout/stderr.
Hermes stages exactly record 378 and the two control-plane paths, commits, pushes, proves
`HEAD == origin/main`, and stops. Every unrelated dirty path remains present and unstaged.

No edit to record 376, developer path, test/fixture/CLI path, pytest, lint, standalone planner,
listing, network/data or real-state access, acquisition, cleanup, migration, transition, later
gate, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/377_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_STOP.md`;
  and
- `tickets/CEX-002.md`.

Implementation evidence correction, developer bytes, real state/data, and every unrelated dirty
path remain excluded.
