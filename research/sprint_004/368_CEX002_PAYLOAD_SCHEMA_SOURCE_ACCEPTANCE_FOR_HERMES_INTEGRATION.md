# CEX-002 Payload-Schema Source Acceptance for Hermes Integration

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact Review-367 source/test correction accepted for bounded Hermes integration
- **Source actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Integration actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Static acceptance

The reviewer independently inspected the complete two-path diff and rehashed both files. Sol's
correction is accepted for integration at these exact identities:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `06d43d085e3d38d8af9043ebc6a5353c8d7de8bf9bd9cde0ac6e3e94b9e6e553`
  - lines: 5,095
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `e708e7ac9ddf183fd2702cfca97677a5dc761966819f9f1aedecb81106704630`
  - lines: 2,593

The production change preserves the exact envelope and nine common fields, then requires exactly
one writer-authoritative family field: exact-bool `consumable` for `daily/metrics`, or exact-text
`etag` for `daily/bookTicker`. Unknown or missing family-specific fields still fail closed, and
the existing later family/key/symbol/date/value checks remain unchanged. The synthetic builder
now emits both production shapes. Direct positive coverage proves each shape; eight negative
cases cover both families across missing, cross-family, additional, and wrong-type fields. No
CLI, fixture, architecture, listing, sidecar, checkpoint, manifest, capacity, publication,
recovery, or authorization logic changed.

Sol ran the one Review-367 command exactly once:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

It exited 0 with this complete output:

```text
........................................................................ [ 60%]
...............................................                          [100%]
```

The run collected 119 cases from 59 test functions. Sol reports no other test, lint, repository-
control, standalone-planner, network/data, real-state, integration, record, or Git operation.
The reviewer did not rerun the command. This is source/test acceptance for integration only; it
does not integrate the drop, accept a real candidate, authorize a retry, or pass Gate 2.

## Hermes integration authorization

Hermes must first read `AGENTS.md`, the current task, CEX-002, ADR-0031, records 366-368, prove
`HEAD == origin/main` at this review's publication commit, verify the staging area is empty, and
rehash the two accepted developer paths. A mismatch stops before validation.

Hermes is authorized to stage only the two accepted developer paths and run exactly, in order:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/369_CEX002_PAYLOAD_SCHEMA_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Hermes stops on the first nonzero result and must not patch the accepted bytes. If every command
exits zero, Hermes creates
`research/sprint_004/369_CEX002_PAYLOAD_SCHEMA_INTEGRATION_RECORD.md` containing both hashes, all
exact commands, complete outputs and exit codes, case/warning results, and the exact staged path
list. It updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002 and Gate 2
`IN_PROGRESS`, name the reviewer as next actor, keep next ticket `NONE`, and state that real
planner retry/resume and all acquisition/transition/later work remain unauthorized.

Hermes stages exactly the two developer paths plus record 369, `CURRENT_TASK.md`, and
`tickets/CEX-002.md`; verifies no other path is staged; commits; pushes `main`; proves
`HEAD == origin/main`; and stops for reviewer inspection. Harness output is a handoff aid only;
the command evidence and final state must be repository-native. Every unrelated dirty path must
remain present and unstaged.

No standalone planner/CLI, listing request, raw ZIP GET, real SQLite/data access, acquisition,
cleanup, migration, generation transition, Gate 3, model work, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/368_CEX002_PAYLOAD_SCHEMA_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`;
  and
- `tickets/CEX-002.md`.

Developer paths, implementation evidence, real state/data, and every unrelated dirty path remain
excluded from this reviewer publication.
