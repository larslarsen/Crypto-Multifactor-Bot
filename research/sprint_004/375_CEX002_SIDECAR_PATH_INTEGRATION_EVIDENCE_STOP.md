# CEX-002 Sidecar-Path Integration Evidence Stop

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact developer integration and pytest/ruff evidence accepted; repository-control/diff evidence incomplete
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reviewer inspection

The reviewer independently confirms that Hermes commit
`291d066322cc3368c34552a6f5257ee4059cd8f6` contains exactly the two Review-373 developer paths,
record 374, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; `HEAD == origin/main`; both accepted hashes
and line counts match; both top-level actor fields name the reviewer; staging is empty; and every
unrelated dirty path remains present and unstaged.

Record 374 durably contains the exact targeted pytest and ruff commands and their complete zero
results: all 123 cases passed with no warnings, and ruff reported `All checks passed!`. The exact
developer integration and those two results are accepted.

Record 374 does not satisfy Review 373's remaining evidence contract. Its repository-control and
scoped-diff section paraphrases that both commands ran and passed, but omits both commands' exact
outputs and explicit exit codes. Harness chat reported those facts, but chat is not repository
authority and cannot complete acceptance. The record's final actor-field ordering is otherwise
correct. The source/test bytes must not be changed or revalidated; only the missing repository-
native command evidence remains open.

No real planner retry, candidate acceptance, or Gate-2 acceptance is authorized.

## Exact Hermes evidence completion

Hermes is authorized to create only
`research/sprint_004/376_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_COMPLETION.md` and update the two
control-plane paths. Before any command it must read `AGENTS.md`, the current task, CEX-002, and
records 373-375; prove `HEAD == origin/main == 291d066322cc3368c34552a6f5257ee4059cd8f6`;
prove empty staging; rehash the two installed developer paths; and make no source/test change.

Hermes must create the final record 376 and set both top-level actor fields to the reviewer before
running either command. The draft record may state the authorized expected zero results, but it
may be committed only if the real results match exactly. Hermes then runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/376_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_COMPLETION.md tickets/CEX-002.md
```

The required results are exit 0 with exact stdout `Repo control check: PASS` and no stderr for
the first command, and exit 0 with empty stdout/stderr for the second. Any difference stops with
no commit or patch. If both match, record 376 is repository-native evidence for the exact
commands, outputs, exit codes, precondition hashes, actor ordering, and final scoped path list.

Hermes stages exactly record 376, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other
path is staged; commits; pushes `main`; proves `HEAD == origin/main`; and stops for reviewer
inspection. It preserves every unrelated dirty path. No pytest, lint, source/test edit,
standalone planner/CLI, listing, network/data or real-state access, acquisition, cleanup,
migration, transition, later gate, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/375_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_STOP.md`; and
- `tickets/CEX-002.md`.

Developer paths, implementation evidence completion, real state/data, and every unrelated dirty
path remain excluded.
