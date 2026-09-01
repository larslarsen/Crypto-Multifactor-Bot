# CEX-002 Sidecar-Path Source Acceptance for Hermes Integration

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact Review-372 source/test correction accepted for bounded Hermes integration
- **Source actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Integration actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Static acceptance

The reviewer independently inspected the complete two-path diff and rehashed both files. Sol's
correction is accepted for integration at these exact identities:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
  - lines: 5,096
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `aa4a09b4c8bee732515961c09ac890ef83f69be6395dd9c3770c4383ee05b149`
  - lines: 2,646

The production change derives the exact stored sidecar string from
`generation["authority_destination"]`, which `_bind_generation0()` already requires to equal the
pinned `data/cex002_qualify`, then appends the fixed `gate2/content/<shard>/<digest>` components.
It performs no path normalization and accepts no alias. Physical bytes continue to be opened
only as exact shard/digest children of the held and rebound content-root descriptor, then checked
for digest, size, bounded sidecar bytes, filename, and provider checksum. The obsolete absolute
physical-root argument is removed from fresh construction and completed-candidate recovery alike.

The synthetic writer now separates physical temporary placement from the exact production-
relative durable string. A direct end-to-end positive case proves that form. Four negative cases
reject an absolute physical spelling, dot/traversal spelling, wrong shard, and wrong digest leaf.
No CLI, fixture, architecture, payload, listing, checkpoint, manifest, capacity, publication,
recovery, or authorization behavior otherwise changed.

Sol ran the one Review-372 command exactly once:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

It exited 0 with no warnings and this complete output:

```text
........................................................................ [ 58%]
...................................................                      [100%]
```

The run collected 123 cases from 60 test functions. Sol reports no other test, lint, repository-
control, standalone-planner, network/data, real-state, integration, record, or Git operation.
The reviewer did not rerun the command. This is source/test acceptance for integration only; it
does not integrate the drop, accept a candidate, authorize a real retry, or pass Gate 2.

## Hermes integration authorization

Hermes must read `AGENTS.md`, the current task, CEX-002, ADR-0031, records 371-373, prove
`HEAD == origin/main` at this review's publication commit, prove empty staging, and rehash the two
accepted developer paths. A mismatch stops before validation.

Hermes is authorized to stage only the two accepted developer paths and run exactly:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/374_CEX002_SIDECAR_PATH_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Hermes stops on the first nonzero result and must not patch the accepted bytes. After pytest and
ruff pass, but before repository control, Hermes must create
`research/sprint_004/374_CEX002_SIDECAR_PATH_INTEGRATION_RECORD.md` and update both top-level
control-plane actor fields to the reviewer. Record 374 must contain both hashes, all exact
commands, complete outputs/exit codes, case/warning results, the exact staged path list, and must
state that the final actor fields existed before repository control. No top-level actor field may
change after repository control. The scoped diff check runs against the final repository bytes.

Hermes stages exactly the two developer paths plus record 374, `CURRENT_TASK.md`, and
`tickets/CEX-002.md`; verifies no other path is staged; commits; pushes `main`; proves
`HEAD == origin/main`; and stops for reviewer inspection. Harness output is a handoff aid only;
all command evidence and state must be repository-native. Every unrelated dirty path remains
present and unstaged.

No standalone planner/CLI, listing request, raw ZIP GET, real SQLite/data access, acquisition,
cleanup, migration, generation transition, Gate 3, model work, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/373_CEX002_SIDECAR_PATH_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`;
  and
- `tickets/CEX-002.md`.

Developer paths, implementation evidence, real state/data, and every unrelated dirty path remain
excluded from this reviewer publication.
