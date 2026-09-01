# CEX-002 Sidecar-Path Integration Record

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Review-373 sidecar-path serialization correction integrated; both validation commands passed
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Authority proof

- **HEAD:** `5e08b1447ad0625e2945a57f39d8405663b0c499`
- **origin/main:** `5e08b1447ad0625e2945a57f39d8405663b0c499`
- **HEAD == origin/main:** true
- **Staging area:** empty at validation time

## Accepted developer path proof

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
  - Lines: 5,096
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `aa4a09b4c8bee732515961c09ac890ef83f69be6395dd9c3770c4383ee05b149`
  - Lines: 2,646

Both installed identities exactly match Review 373.

## Validation commands and outputs

### Command 1: pytest

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

- **Exit code:** 0
- **Output:**
  ```text
  ........................................................................ [ 58%]
 ...................................................                      [100%]
  ```
- **Cases collected:** 123
- **Cases passed:** 123
- **Warnings:** none

### Command 2: ruff

```text
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

- **Exit code:** 0
- **Output:** `All checks passed!`

## Repository control and diff

Repository control (`python3 scripts/check_repo_control.py`) and the scoped diff check (`git diff --check`) run after this record and both final actor fields exist, against the final repository bytes. Both top-level control-plane actor fields were set to the reviewer before repository control. No top-level actor field changes after repository control.

## Authorized staged paths

Hermes stages exactly these five paths:

1. `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
2. `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
3. `research/sprint_004/374_CEX002_SIDECAR_PATH_INTEGRATION_RECORD.md`
4. `docs/handoff/CURRENT_TASK.md`
5. `tickets/CEX-002.md`

No other path is staged. Every unrelated dirty path remains present and unstaged.

## Stop condition

After commit and push, Hermes proves `HEAD == origin/main` and stops for reviewer inspection. No standalone planner/CLI, listing request, raw ZIP GET, real SQLite/data access, acquisition, cleanup, migration, generation transition, Gate 3, model work, or next ticket is authorized.
