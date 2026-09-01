# CEX-002 Sol V3 Reachability Source Acceptance for Hermes Integration

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact Review-398 corrected source/test drop accepted for bounded Hermes integration
- **Source actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Integration actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Static acceptance

The reviewer independently inspected the complete two-path diff, rehashed both files, and accepts
the ADR-0033 source/test drop for integration at exactly these identities:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32`
  - lines: 5,147
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905`
  - lines: 3,342
  - test functions: 70

The production source selects only the fresh fixed `gate2_revision_candidate_v3` sibling and uses
distinct ADR-0033 v3 candidate, checkpoint, lineage, locator, and policy identities. V1 and v2 are
not referenced, imported, renamed, copied, hard-linked, mutated, or authenticated as v3.

Each pass retains the existing complete authenticated ListObjectsV2 traversal, request echo,
retained-page, token-cycle, bound, checkpoint, and recovery rules. Cross-pass equality now uses a
canonical document containing exact roots, exact discovered/completed prefixes, and each prefix's
sorted aggregate child-prefix set. Any namespace drift blocks. Page ordinal, count, truncation
sequence, current/next cursors, request keys, response identities, URLs, headers, and retrieval
clocks remain exact physical checkpoint/lineage facts but no longer define cross-pass semantic
equality.

Every frozen pending raw object and sidecar still must exist in both passes and match exact key,
size, and ETag, including the single-part sidecar rule. The v3 receipt and lineage replace the
stable page-graph claim with `stable_reachability_sha256` while retaining the stable pending-facts
count/digest. Total and per-pass page counts remain exact ordinary receipt/lineage claims but are
projected out of `semantic_sha256`. Exact pass-2 manifest locators remain physical and the
transport-stripped semantic-row digest remains authenticated. The volatile local
`capacity_projection` remains exact locator-bound physical receipt evidence and is excluded from
semantic identity, per Review 398's ADR clarification.

Focused tests prove v1/v2/v3 isolation and cross-version recovery refusal; opaque-cursor and
unrelated page-boundary equivalence; one-page versus truncated-plus-terminal complete passes;
equal semantic but distinct physical candidates; exact physical lineage and recovery; aggregate
child-prefix drift refusal; forged root/discovered/completed state refusal; pending raw/sidecar
absence, key, size, and ETag drift refusal; and the existing incomplete, malformed, cyclic,
unauthenticated, ceiling, resume, publication, ZIP, held-descriptor, and no-authorization safety
invariants.

The final scoped diff is whitespace-clean and contains 47 additions/50 deletions in production
plus 316 additions/114 deletions in test source. No other path belongs to the Sol drop.

## Targeted source feedback

The first Review-397 targeted run exited 1 at the now-removed capacity semantic expansion; Review
398 rejected that stopped drop and authorized exactly two corrective lines. Sol made only those
two corrections and ran Review 398's one exact command:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

It exited 0 with all 147 collected cases passing and this complete output:

```text
........................................................................ [ 48%]
........................................................................ [ 97%]
...                                                                      [100%]
```

Sol reports no other post-Review-398 Python/test run, planner, CLI, acquisition, network, real-data,
SQLite, Git, record, cleanup, integration, or transition action. The reviewer independently
verified the final hashes, line/function counts, scope, and whitespace but did not rerun pytest.
Harness output is source-drop handoff evidence; this repository review is the acceptance decision.

This is source/test acceptance for integration only. It does not integrate the drop, accept a v3
candidate, authorize a real listing run or raw acquisition, pass Gate 2, or authorize later work.

## Hermes integration authorization

Hermes must read `AGENTS.md`, the current task, full CEX-002 ticket, ADR-0033, and Reviews 397-399.
It must prove `HEAD == origin/main` at this review's publication commit, prove staging is empty,
and rehash the two accepted developer paths. Any mismatch stops before validation. The 11
unrelated modified and 13 unrelated untracked paths must remain present, unchanged, and unstaged.

Hermes may integrate only the two accepted developer paths and run exactly, in order:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Hermes stops on the first nonzero result and must not patch either accepted developer path. After
pytest and ruff pass, but before repository control, Hermes must create
`research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md` and update both top-level
control-plane actor fields to the reviewer. Record 400 must contain the two accepted hashes, exact
preflight facts, every exact command, complete stdout/stderr and exit code, the exact collected
case/warning results, and the final staged path list. The final actor fields must exist before
repository control and may not change afterward. Record 400 must contain the exact
repository-control result before scoped diff runs; scoped diff must run against the final five
repository files, and none may change afterward.

If and only if all four commands pass, Hermes stages exactly the two developer paths, record 400,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other staged path; commits;
pushes `main`; proves `HEAD == origin/main`; and stops for reviewer inspection. Git is authorized
only for those mechanical integration/publication actions. Harness output remains a handoff aid
and cannot replace record 400.

No standalone planner/CLI, listing request, raw ZIP GET, real v1/v2/v3 candidate or generation-0
data access, SQLite open, acquisition, cleanup, migration, generation transition, later gate/model
work, or next ticket is authorized. CEX-002 and Gate 2 remain `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/399_CEX002_SOL_V3_REACHABILITY_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`;
  and
- `tickets/CEX-002.md`.

The accepted developer paths remain unintegrated and unstaged until Hermes publishes them.
Implementation evidence, real state/data, and every unrelated dirty path remain excluded.
