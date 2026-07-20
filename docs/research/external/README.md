# External Research — Triage Policy

This directory holds **external advisory research** delivered outside the repository's
engineering control plane (e.g. Deep Research reports, vendor or third-party audits).
These documents are **informational only** until a reviewer triages them.

## Rules

- External reports **must not** change frozen architecture, the roadmap, tickets,
  or acceptance records on their own.
- Repository documents (`README.md`, `docs/architecture/*`, `tickets/*`,
  `docs/handoff/CURRENT_TASK.md`) and the **current code** remain the authoritative
  source of truth.
- Each report carries a metadata notice stating the audited snapshot, its
  classification, and that embedded `turn…` citations are session-local Deep
  Research references that may not resolve outside the originating report.
- To act on a recommendation, a reviewer opens a ticket (or extends an active one)
  through the normal control plane. The report's findings become engineering work
  only via that ticket — never by editing repo artifacts directly from the report.

## Current contents

- `2026-07_deep_research_architecture_audit_8066b4e.md` — external architecture
  audit of snapshot `8066b4ecd91e634d0d1a29a391227964108cf4e4`. Documentation-only
  drop; not an architecture, roadmap, or acceptance change.
