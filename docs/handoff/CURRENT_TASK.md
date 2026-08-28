# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - permission-corrected review-327 continuation
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Immediate state: review 326 accepted the complete ADR-0030 source/test correction. Hermes's
first `git add` failed because its sandbox mounted `.git` read-only. No file was staged, no
index lock remains, no commit exists, and focused Ruff/targeted pytest remain unrun. The
accepted two dirty source/test files are intact; the rejected real Gate-2 store remains
untouched.

Hermes must follow review 327's short continuation using explicit Git-write escalation for
every command that writes `.git`: reconfirm head/hashes/empty index, integrate only the two
accepted files, then run review 326's focused Ruff and targeted pytest once each in order.
Stop on any denial or failure without repair/rerun. On two passes, publish renumbered evidence
record 328 with approved Git writes, run final shared-tree `git diff --check` once, and stop.

Real-store access/retirement, corrected planning, acquisition, replay, `verify`, full-suite or
repository-wide validation, control, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, experiments, PAPER/LIVE, and next-ticket work remain unauthorized. Next ticket is
`NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `docs/adr/0030-exact-retained-credit-and-pre-network-plan-retirement.md`
- `research/sprint_004/326_CEX002_RETAINED_AUTHORITY_SOURCE_ACCEPTANCE_AND_INTEGRATION.md`
- `research/sprint_004/327_CEX002_HERMES_GIT_SANDBOX_CORRECTION.md`
