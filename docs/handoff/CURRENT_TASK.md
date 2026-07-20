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

## Authorized scope

Implement BAR-001 only. Sr Dev - Grok Build owns production-source reasoning and edits:
publish schema-conformant canonical intraday bars only from quality-accepted immutable
source datasets; enforce explicit venue/instrument/interval/time/unit/availability
semantics, stable sorting and uniqueness; derive deterministic daily bars; reconcile
against source-native daily bars with explicit tolerances and quarantine; and expose
partition-size measurements. Preserve dataset IDs, manifests, lineage, UTC semantics,
and fail-closed quality behavior. No network acquisition, migration, architecture change,
tests, records, Git, commits, or pushes. Stop after the source drop is ready for Jr
integration.

After the Sr drop, Jr Dev - Hermes owns integration, focused tests, acceptance commands,
change report, repository control, Git, commit, and push. Do not begin another ticket.
