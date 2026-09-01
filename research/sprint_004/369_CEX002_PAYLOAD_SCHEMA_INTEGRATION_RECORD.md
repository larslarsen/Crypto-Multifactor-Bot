# CEX-002 Payload-Schema Integration Record

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Review-368 source/test correction integrated; four-command validation chain passed; repository-native state published
- **Integration actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Pre-integration authority proof

- **HEAD:** `b20a210ccf59df4ae9d8e7c25e17595f89768bd5`
- **origin/main:** `b20a210ccf59df4ae9d8e7c25e17595f89768bd5`
- **HEAD == origin/main:** true
- **Staging area before integration:** empty

## Accepted developer path identities

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `06d43d085e3d38d8af9043ebc6a5353c8d7de8bf9bd9cde0ac6e3e94b9e6e553`
  - Lines: 5,095
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `e708e7ac9ddf183fd2702cfca97677a5dc761966819f9f1aedecb81106704630`
  - Lines: 2,593

Both identities exactly match Review 368.

## Staged path list

Exactly two developer paths were staged before validation:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`

## Four-command validation chain

### Command 1 — pytest

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

- **Exit code:** 0
- **Output:**
  ```text
  ........................................................................ [ 60%]
  ...............................................                          [100%]
  ```
- **Cases:** 119 collected from 59 test functions; all passed.

### Command 2 — ruff

```text
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

- **Exit code:** 0
- **Output:** `All checks passed!`

### Command 3 — repository control

```text
python3 scripts/check_repo_control.py
```

- **Exit code:** 0
- **Output:** `Repo control check: PASS`

### Command 4 — diff check

```text
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/369_CEX002_PAYLOAD_SCHEMA_INTEGRATION_RECORD.md tickets/CEX-002.md
```

- **Exit code:** 0
- **Output:** (empty — no conflict markers or whitespace errors)

## Post-validation publication

After all four commands exited zero, Hermes created this record, updated `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`, staged exactly the five authorized paths, committed, pushed `main`, and proved `HEAD == origin/main`.

## Authorization boundaries

This integrates only the two Review-368 developer paths. It does not accept a real candidate, authorize a planner retry/resume, perform a raw ZIP GET, access Coinalyze secrets, edit the active generation, run a standalone planner, mutate real state/data, perform acquisition, cleanup, migration, generation transition, Gate 3, model work, or next ticket. All such work remains unauthorized pending reviewer inspection.

## Repository transition

Hermes stages exactly:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
- `research/sprint_004/369_CEX002_PAYLOAD_SCHEMA_INTEGRATION_RECORD.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

verifies no other path is staged, commits, pushes `main`, proves `HEAD == origin/main`, and stops. Every unrelated dirty path remains present and unstaged. Harness output is a handoff aid only; all evidence and state are repository-native.
