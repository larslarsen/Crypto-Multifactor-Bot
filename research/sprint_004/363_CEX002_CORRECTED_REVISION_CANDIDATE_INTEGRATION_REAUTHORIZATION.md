# CEX-002 Corrected Revision-Candidate Integration Reauthorization

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact corrected drop accepted for bounded Hermes integration
- **Corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Next actor:** Jr Dev - Hermes through the installed Hermes harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Corrected identity and decision

Sol made exactly Review 362's authorized one-line test correction. In
`test_locator_recovery_recomputes_canonical_receipt_claims`, the test now requires the prerequisite
candidate creation to exit `EXIT_COMPLETE` before it forges the completed receipt. The reviewer
statically confirmed that exact insertion and independently rehashed the drop.

The six accepted integration identities are now:

- production: SHA-256
  `b8c60212ababc9f620afcf71725cac00f9f2893408f3f12f5fb947670cd03e86`, 5,084 lines;
- CLI: SHA-256
  `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`, 87 lines;
- corrected test source: SHA-256
  `065e6a229c58c72b6b7a90ad27aa806c4cf3afc729321066f65644f6090795c1`, 2,519 lines;
- book-ticker fixture: SHA-256
  `dd53323a7fcab0c39c8dd8d4824446fddc95b993c44671ead27144b064d84569`;
- metrics fixture: SHA-256
  `d96c6713a29694264d5f3232bc04e085840b19d96d7f673e246ed36f473c5947`;
- checksum fixture: SHA-256
  `6dd7148990cd11f7b30e8de9bedd0fea88338c718ab20e3c1c58ee9238abbf55`.

All production, CLI, and fixture bytes remain identical to Review 361. The previous test identity
is superseded only by the exact prerequisite assertion. Sol attests that it ran no Python, test,
lint, planner, network/data, integration, record, or Git command and edited no other byte/path.

The corrected source/test drop is accepted for Hermes integration. This is not a real-candidate
or Gate-2 acceptance and does not authorize planner execution.

## Hermes integration reauthorization

Hermes must rehash and stage only these six identities and run exactly:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py scripts/research/plan_binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py scripts/research/plan_binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate docs/handoff/CURRENT_TASK.md research/sprint_004/364_CEX002_REVISION_CANDIDATE_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Hermes stops on the first nonzero result and does not patch accepted developer bytes. If every
command exits zero, it creates
`research/sprint_004/364_CEX002_REVISION_CANDIDATE_INTEGRATION_RECORD.md` containing the hashes,
exact commands, complete outputs, exit codes, 109-case and clean-warning result, and exact staged
path list. It updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002
`IN_PROGRESS`, name the reviewer as next actor, keep next ticket `NONE`, and state that real
planner/acquisition execution remains unauthorized.

Hermes stages exactly the six developer paths plus record 364, `CURRENT_TASK.md`, and
`tickets/CEX-002.md`; verifies no other staged path; commits; pushes `main`; proves
`HEAD == origin/main`; and stops for reviewer inspection. The harness output is a handoff aid
only; command evidence and state must be durable in record 364 and the control plane.

Hermes must preserve all unrelated dirty paths unstaged and unchanged. No network request other
than the authorized Git push, real SQLite/data open, standalone planner/CLI, listing, acquisition,
cleanup, migration, generation transition, later gate, model, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/363_CEX002_CORRECTED_REVISION_CANDIDATE_INTEGRATION_REAUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

Developer paths, real state/data, implementation evidence, and every unrelated dirty path remain
excluded until Hermes integration.
