# CEX-002 Hermes Integration Validation Stop

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** integration stopped before commit; one-line test correction required
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Durable execution disposition

At the owner's explicit direction, the reviewer invoked the installed Hermes harness for the
one-way Review-361 integration assignment. This record promotes the resulting stop and reviewer
decision into the repository control plane; the harness response itself is not an acceptance or
decision surface.

Hermes reported this exact ordered result:

1. all six Review-361 SHA-256 identities matched;
2. exactly the six accepted developer paths were staged and verified;
3. the targeted pytest exited zero with all 109 collected cases passing and no warning output;
4. the targeted ruff command was the first nonzero result, exiting one with:

```text
F841 Local variable `complete` is assigned to but never used
    --> tests/acquisition/test_binance_usdm_gate2_revision_candidate.py:1094:5
```

Hermes stopped without patching accepted bytes, unstaged all six paths, created no implementation
record, made no commit or push, and reported `HEAD == origin/main == f3c3915`. The reviewer
independently confirmed that the staging area is empty, the six accepted hashes remain exact,
`HEAD == origin/main == f3c39152713303ee350065875f4bc29ab8727cc0`, and all unrelated dirty
paths remain present and unstaged. The reviewer did not rerun pytest, ruff, repository control,
or any planner/data command.

The Review-361 source acceptance remains technically valid except for integration eligibility of
the exact test-source byte identity. No production, CLI, or fixture correction is required. No
Hermes integration record 362 was created because Review 361 correctly reserved it for a fully
successful command chain; this reviewer record is the numbered validation-stop disposition.

## Exact corrective authorization

Sr Dev - Codex Sol using GPT-5.6-sol High is authorized for one test-source-only correction at:

`tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`

In `test_locator_recovery_recomputes_canonical_receipt_claims`, preserve the existing
`complete = _run(...)` assignment and immediately assert:

```text
assert complete["exit_code"] == planner.EXIT_COMPLETE
```

This both consumes the variable and strengthens the test's prerequisite. Sol must make no other
source/test/fixture/CLI or repository change. It may use static read-only inspection and exact
hash/line accounting only. It performs no Python, pytest, ruff, repository-control, planner,
network/data, real-state, integration, record, Git, commit, or push command. It reports the exact
new test SHA-256 and line count and stops for reviewer static inspection.

Hermes is unauthorized until the reviewer accepts that exact correction and republishes the
integration assignment. No real planner, listing, acquisition, cleanup, migration, generation
transition, Gate 3, model, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next
ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/362_CEX002_HERMES_INTEGRATION_VALIDATION_STOP.md`; and
- `tickets/CEX-002.md`.

Developer paths, real state/data, implementation evidence, and every unrelated dirty path are
excluded.
