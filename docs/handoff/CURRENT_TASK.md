# CURRENT_TASK

Ticket: BAR-001
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Sr Dev - Grok Build

Accepted dependency: BIN-001 at
`b881335817e9390011a37afb73b522d985746416` (REVIEW-0025).

## Governing documents

- tickets/BAR-001.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/architecture/07_IMPLEMENTATION_ROADMAP.md
- docs/reviews/REVIEW-0025_BIN-001_ACCEPTED.md
- docs/reviews/REVIEW-0027_BAR-001_CHANGES_REQUIRED.md

## Authorized scope

Complete the source remediation in REVIEW-0027. Sr Dev - Grok Build owns production
source only: enforce verified immutable MAN-001 input identity/quality, nullable missing
values, warning propagation, strict source schema/interval semantics, complete-day gates,
order-independent duplicate failure, and valid lineage. Preserve deterministic
partitioning/reconciliation and no-network behavior. No migration, architecture change,
tests, records, Git, commits, or pushes. Stop after the source drop is ready for Jr
integration.

After the Sr drop, Jr Dev - Hermes owns integration, focused tests, acceptance commands,
change report, repository control, Git, commit, and push. Do not begin another ticket.
