# REVIEW-0005 — AUD-001-labelled toolkit commits: CHANGES_REQUIRED

**Review date:** 2026-07-18
**Decision:** changes_required - RESOLVED (superseded by AUD-002 / REVIEW-0007_AUD-002_FINAL.md; AUD-002 ACCEPTED)
**Architecture impact:** none (governance / ticket re-scoping)
**ADR required:** no

## Scope

Documents the review outcome of the source-audit toolkit commits that were merged under the
`AUD-001` label prior to this review, and their prospective governance.

## Commits reviewed (provisional, under AUD-001 label)

- `3a737df` — AUD-001: source_audit toolkit + ruff clean + mypy clean + 60 tests
- `c856083` — AUD-001: mark ticket landing status complete
- `1aa6967` — AUD-001: Resumed source_audit development - bars.py reconstruction implemented
- `247787b` — AUD-001: silence intentional re-export F401

These commits delivered the initial `src/source_audit/` package (ZIP/CSV audit, atomic download
stub, timestamp inference, bars reconstruction, storage statistics, deterministic serialization)
and achieved a green unrelated-repository test suite, ruff 0, and mypy clean.

## Decision: CHANGES_REQUIRED

The work is reviewed as `CHANGES_REQUIRED`. The commits were provisional: the toolkit is not yet
a completed, reviewed deliverable, and the AUD-001 label on these commits referred to toolkit
work that is now tracked separately from the `AUD-001` schema/coverage-profiler ticket.

## Prospective governance

- A new ticket, `AUD-002` (Complete the reusable source-audit toolkit), governs this work going
  forward. `AUD-002` covers `src/source_audit/`, source-audit-focused test code, atomic
  content-addressed downloads, safe archive and CSV inspection, timestamp inference, Binance
  precision comparison, robust pagination, trade-to-bar reconstruction and candle comparison,
  storage statistics, and deterministic serialization.
- Existing commits through `247787b` remain provisional and incomplete. Passing unrelated
  repository tests does not constitute acceptance.
- Git history is **not** rewritten. The provisional commits stand; completion work proceeds under
  `AUD-002` and is reviewed independently.

## Out of scope for this review

No real source data, research conclusions, architecture changes, or provider acceptance
decisions are introduced or decided here.

## Decision

Mark the prior AUD-001-labelled toolkit commits `CHANGES_REQUIRED`; govern the toolkit
prospectively under `AUD-002`. No history rewrite.
