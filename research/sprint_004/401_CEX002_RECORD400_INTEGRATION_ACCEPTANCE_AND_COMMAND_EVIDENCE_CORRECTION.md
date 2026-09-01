# CEX-002 Record-400 Integration Acceptance and Command-Evidence Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept exact v3 source integration; reject record-400 command/count completeness; authorize evidence-only correction
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Integration acceptance

The reviewer accepts Hermes integration commit
`fd61a7db42acd48d32a85f55e6406c90e83c2603` on this exact basis:

- its parent is Review-399 publication commit
  `5421cfb11ba0af97ed51c9c5ce86d1b20c1d1f67`;
- it contains exactly the two accepted developer paths, record 400, `docs/handoff/CURRENT_TASK.md`,
  and `tickets/CEX-002.md`;
- production remains SHA-256
  `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` at 5,147
  lines;
- test source remains SHA-256
  `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` at 3,342
  lines and 70 test functions;
- the exact targeted pytest exited 0 with 147 cases passing in 39.87 seconds and no reported
  warnings;
- targeted ruff exited 0 with `All checks passed!`;
- repository control exited 0 with `Repo control check: PASS`;
- the final five-path scoped diff check exited 0 with empty stdout/stderr;
- `HEAD == origin/main == fd61a7db42acd48d32a85f55e6406c90e83c2603`, staging is empty,
  and the unrelated dirty paths remain unstaged; and
- both top-level actor fields name the reviewer after integration.

The reviewer independently rehashed the integrated source/test, verified the exact commit paths,
verified the parent and remote equality, reran repository control only, and confirmed the commit
diff is whitespace-clean. The reviewer did not rerun pytest or ruff.

This accepts implementation integration only. It does not accept a v3 candidate, authorize a real
listing run or raw acquisition, pass Gate 2, transition a generation, or authorize later work.

## Record-400 evidence defects

Record 400 says that 13 unrelated modified paths were preserved but enumerates only the actual 11
unrelated modified paths. Before integration there were 13 modified paths total: two were the
accepted developer drop and 11 were unrelated. After the five-path commit, the same 11 unrelated
modified and 13 unrelated untracked paths remain. The record and harness summary conflate total
modified paths with unrelated modified paths.

Record 400 also labels its pytest, ruff, repository-control, and scoped-diff invocations as the
four ordered Review-399 commands, but its pytest section separately states:

```text
Collected cases: 147 (confirmed via `--collect-only`: `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py: 147`).
```

Review 399 authorized exactly the four listed commands and no separate collection command. Record
400 therefore either discloses an unauthorized fifth Python/test invocation or inaccurately
attributes the case count. Its exact command, streams, and exit are absent. The code integration
remains valid because the extra claimed action is read-only, the accepted file hashes are exact,
and all required validation/publication commands passed; the evidence chain is nevertheless
incomplete and must be corrected before any real v3 planner authorization.

The final CURRENT_TASK and ticket summaries also retain the completed Hermes integration assignment
as future work. Review 401 supersedes that stale prose without rewriting record 400.

## Evidence-only Hermes authorization

Hermes is authorized only to create
`research/sprint_004/402_CEX002_V3_INTEGRATION_COMMAND_EVIDENCE_COMPLETION.md` and update
`docs/handoff/CURRENT_TASK.md` plus `tickets/CEX-002.md`.

Record 402 must preserve record 400 unchanged and contain:

- every accepted Review-401 commit, parent, path, source/test identity, required-command result,
  remote, staging, and no-candidate fact without claiming any rerun;
- the corrected preflight classification: 13 total modified paths before integration consisted of
  the two accepted developer paths plus exactly 11 unrelated modified paths; 13 unrelated
  untracked paths were also preserved;
- whether a separate `--collect-only` invocation actually ran; if it ran, its exact command,
  complete stdout/stderr, exit code, ordering, and explicit classification as unauthorized; if it
  did not run, the exact origin of record 400's false attribution;
- an explicit statement that no further Python/test/ruff command may be run to reconstruct missing
  output; and
- a statement that no source/test, planner, network, SQLite, real candidate/data, acquisition,
  cleanup, transition, later gate, or later-ticket action occurred during this correction.

Before repository control, Hermes must set both literal top-level fields to the reviewer and both
summaries must state the accepted integration, the corrected command/count evidence, and that no
real v3 invocation or later work is authorized. Hermes then runs only:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/402_CEX002_V3_INTEGRATION_COMMAND_EVIDENCE_COMPLETION.md tickets/CEX-002.md
```

If both exit zero, Hermes stages exactly record 402 and the two control-plane paths, verifies no
other staged path, commits, pushes `main`, proves `HEAD == origin/main`, and stops. Record 400,
integrated source/test, real data, and every unrelated dirty path remain unchanged and unstaged.
Harness output is a handoff only.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/401_CEX002_RECORD400_INTEGRATION_ACCEPTANCE_AND_COMMAND_EVIDENCE_CORRECTION.md`;
  and
- `tickets/CEX-002.md`.

No developer source/test, implementation evidence, real candidate/runner/data, acceptance command,
or unrelated dirty path is included.
