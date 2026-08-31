# CEX-002 Sol High Revision-Candidate Availability Reroute

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** availability-only senior-source reroute
- **Unavailable actor:** Sr Dev - Claude Build using Claude Opus 5
- **Authorized actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reason and boundary

The owner reports that Claude Build is unavailable and explicitly authorizes Sol High. This is
valid availability evidence under the minimum-capable-usage routing policy. It changes only the
selected formal senior source author; it does not accept Grok's rejected drop, alter Review 356's
technical correction contract, authorize integration, or change ADR-0031.

GPT-5.6-sol High is added as **Sr Dev - Codex Sol**, an alternate formal senior production-code
actor with the same architecture-sensitive source/test-source scope and the same integration,
evidence, Git, data, and publication prohibitions as Grok Build and Claude Build. Exactly one
senior remains authorized for this bounded correction.

## Sol High correction authorization

Sr Dev - Codex Sol using GPT-5.6-sol High must implement every Review-356 finding as one coherent
correction while preserving the accepted portions of Grok's unintegrated drop. Its writable
scope is exactly:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`, only if mechanically required
  by the corrected API;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/` for bounded fixtures only.

Sol may use read-only static inspection commands for the active ticket, governing documents,
and authorized source/test paths. It may not read or inspect `~/cmb_archive/` or open, inspect,
hash, delete, rewrite, or otherwise touch the real generation-0 SQLite/WAL/SHM, content, or
candidate data. It performs no network/data operation, standalone production planner or CLI,
acquisition, migration, integration, repository-record edit, Git operation, commit, push, or
acceptance command.

After completing the source and test-source correction, Sol is authorized under the targeted
senior-test exception to run exactly one command against synthetic pytest-managed temporary
roots:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Sol stops on the first nonzero result. Whether zero or nonzero, it reports the exact command and
complete output, exact SHA-256 and line counts for every edited path, the test-function count,
and confirmation that no other executable/test/network/data/Git command ran. A zero result is
source feedback only and does not integrate or accept the drop. Sol then stops for reviewer
static inspection.

Hermes remains unauthorized. No candidate execution, cleanup, generation transition, corrected
acquisition, Gate 3, model, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS` and
next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS reviewer-publication exception, the reviewer may stage, commit, and push
exactly:

- `AGENTS.md`;
- `docs/engineering/DEVELOPMENT_ROLES.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/357_CEX002_SOL_HIGH_REVISION_CANDIDATE_REROUTE.md`; and
- `tickets/CEX-002.md`.

The unintegrated developer source/test/fixture drop, real data/state, developer evidence, and
all unrelated dirty paths are excluded.
