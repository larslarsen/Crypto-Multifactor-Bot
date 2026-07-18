# ADR-0007 — Architecture freeze and RFC process

**Status:** Accepted

## Decision

The architecture described in `docs/architecture/00_SYSTEM_ARCHITECTURE.md`
(v1, as committed in `ff1300c`) is **frozen** and treated as **RFC-001**.

From the freeze point forward, any change to architecture — components,
domain boundaries, data flow, technology choices, or repository layout — must
be proposed as a new Architecture Decision Record. Silent edits to the
architecture documents are prohibited.

## Rationale

The senior engineer's guidance: freeze the accepted architecture as an RFC and
route every subsequent architecture change through an ADR, so design drift does
not accumulate during implementation. The project is about to enter the
implementation phase (`07_IMPLEMENTATION_ROADMAP.md`), where ad-hoc edits are
most tempting and most corrosive to a clean-room design.

This ADR is itself the freeze mechanism: recording the discipline as a decision
means the discipline is subject to the same ADR process it establishes.

## Consequences

- `docs/architecture/00_SYSTEM_ARCHITECTURE.md` and the `adr/` set are the
  frozen RFC; modify them only via a new ADR that supersedes or amends.
- New architecture changes get the next ADR number (`0008`, `0009`, …),
  monotonically, with a `Status` and a link back to what it amends/supersedes.
- The ADR index (`adr/README.md`) is the single source of truth for accepted
  architecture decisions; it is updated alongside every new ADR.
- Implementation work proceeds against the frozen architecture; code that
  appears to contradict it triggers an ADR, not a quiet architecture edit.
- Drift is detectable: any architecture-doc diff without a corresponding ADR
  reference is rejected in review.
