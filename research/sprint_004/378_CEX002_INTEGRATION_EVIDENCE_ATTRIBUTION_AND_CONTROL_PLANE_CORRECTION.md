# CEX-002 Integration Evidence Attribution and Control-Plane Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record 376's reviewer attribution superseded; integration evidence now complete
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Authority proof

- **HEAD:** `968a996a557d20f199f2e8b5407a87af9365bb4d`
- **origin/main:** `968a996a557d20f199f2e8b5407a87af9365bb4d`
- **HEAD == origin/main:** true
- **Staging area:** empty at validation time

## Accepted developer path proof

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
  - Lines: 5,096
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `aa4a09b4c8bee732515961c09ac890ef83f69be6395dd9c3770c4383ee05b149`
  - Lines: 2,646

Both installed identities exactly match Review 373 and remain unchanged.

## Attribution correction

Record 376 durably supplies the accepted repository-control and scoped-diff command evidence. Its
exact commands, streams, and exit codes are preserved here without claim of a rerun:

### Command 1: repository control

```text
python3 scripts/check_repo_control.py
```

- **Exit code:** 0
- **Stdout:** `Repo control check: PASS`
- **Stderr:** (empty)

### Command 2: scoped diff check

```text
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/376_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_COMPLETION.md tickets/CEX-002.md
```

- **Exit code:** 0
- **Stdout:** (empty)
- **Stderr:** (empty)

Record 376 incorrectly attributed its executing actor as the Lead Quantitative Finance
Researcher/Engineer. The actual executing and publishing actor was Jr Dev - Hermes through the
installed Hermes one-shot harness. Record 376's reviewer attribution is superseded by this
correction, but the historical file is not rewritten and remains immutable evidence.

## Integration evidence completion

The combined records 374, 376, and 378 complete Review 373's integration evidence:

- Record 374 documents the exact pytest and ruff commands and their complete zero results.
- Record 376 documents the exact repository-control and scoped-diff commands, streams, and exit
  codes.
- Record 378 corrects the executing-actor attribution and confirms both control-plane summaries
  now identify the evidence as complete.

## Repository control and scoped-diff evidence

Both top-level actor fields were set to the reviewer before running either command. No top-level
actor field changes after running either command.

### Command 1: repository control

```text
python3 scripts/check_repo_control.py
```

- **Exit code:** 0
- **Stdout:** `Repo control check: PASS`
- **Stderr:** (empty)

### Command 2: scoped diff check

```text
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/378_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_CORRECTION.md tickets/CEX-002.md
```

- **Exit code:** 0
- **Stdout:** (empty)
- **Stderr:** (empty)

## Authorized staged paths

Hermes stages exactly these three paths:

1. `research/sprint_004/378_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_CORRECTION.md`
2. `docs/handoff/CURRENT_TASK.md`
3. `tickets/CEX-002.md`

No other path is staged. Every unrelated dirty path remains present and unstaged.

## Stop condition

After commit and push, Hermes proves `HEAD == origin/main` and stops for reviewer inspection.
No source/test edit, pytest, lint, standalone planner, listing, network/data or real-state
access, acquisition, cleanup, migration, transition, later gate, or next ticket is authorized.
