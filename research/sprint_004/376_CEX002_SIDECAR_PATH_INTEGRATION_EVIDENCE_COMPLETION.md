# CEX-002 Sidecar-Path Integration Evidence Completion

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** repository-control and scoped-diff evidence completed; Review-375 integration evidence now complete
- **Executing actor:** Lead Quantitative Finance Researcher/Engineer
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Authority proof

- **HEAD:** `be6dd639154450a27d43ad62cc40b3f972e3cf87`
- **origin/main:** `be6dd639154450a27d43ad62cc40b3f972e3cf87`
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

## Repository control and scoped-diff evidence

Both top-level actor fields were set to the reviewer before running either command. No top-level actor field changes after running either command.

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

## Authorized staged paths

Hermes stages exactly these three paths:

1. `research/sprint_004/376_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_COMPLETION.md`
2. `docs/handoff/CURRENT_TASK.md`
3. `tickets/CEX-002.md`

No other path is staged. Every unrelated dirty path remains present and unstaged.

## Stop condition

After commit and push, Hermes proves `HEAD == origin/main` and stops for reviewer inspection. No standalone planner/CLI, listing request, raw ZIP GET, real SQLite/data access, acquisition, cleanup, migration, generation transition, Gate 3, model work, or next ticket is authorized.
