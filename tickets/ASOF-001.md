# ASOF-001 — As-Of Access API

**Priority:** P0
**Status:** AWAITING_REVIEW
**Dependencies:** CAT-001/CAT-001A, REF-001, BAR-001, FEE-001 (accepted)
**Layer:** catalog (as-of access)
**Architecture:** implements existing Phase 3 AsOfStore contract (`docs/architecture/03_DOMAIN_INTERFACES.md` §6; eligibility from `01_DATA_ARCHITECTURE.md` §12); no ADR required

## Objective

Provide a single reviewed as-of access implementation so factor and research code never perform
ad-hoc temporal joins. The store enforces strict observation and reference bitemporal eligibility
against published market-bar datasets (BAR-001) and control-catalog reference tables (REF-001,
FEE-001).

## Required Contract

- Public `AsOfStore` protocol with `latest_available` and `as_of`.
- Concrete catalog implementation that returns Apache Arrow tables.
- Eligibility for a decision time `t` and knowledge time `k`:
  - `valid_from <= t < valid_to` (open upper bound allowed);
  - `availability_time <= t` when the row carries availability;
  - for reference facts: `known_from <= k < known_to` (open upper bound allowed).
- `latest_available` selects, per key, the latest eligible observation at `decision_time`, optionally
  rejecting rows older than `max_age`.
- `as_of` returns all eligible rows at `(decision_time, knowledge_time)` without inventing values.
- Missing keys / no eligible rows return an empty table (or empty partition for that key), never a
  silent zero or venue fallback.
- Factor code must not reimplement as-of joins.

## Dataset Surface

| Source | Ticket | Access path |
|--------|--------|-------------|
| Canonical market bars | BAR-001 | MAN-001 `dataset_id` with `dataset_type=market_bars` |
| Instrument versions | REF-001 | Logical id `ref_instrument_version` over control SQLite |
| Fee schedules | FEE-001 | Logical id `ref_fee_schedule` over control SQLite |

## Deliverables

- `src/cryptofactors/catalog/as_of.py` — protocol, eligibility, store implementation.
- Public exports from `cryptofactors.catalog`.
- Ticket authorization record (`tickets/ASOF-001.md`).

## Out Of Scope

- Tests, fixtures, CLI, network, Git, commits, pushes.
- Universe, factors, labels, portfolio, live serving.
- Changing BAR-001 / REF-001 / FEE-001 write paths or migrations.
- Ad-hoc “latest” files or path-based identity.

## Stop Condition

After Sr production source and this ticket file are in the local worktree, stop for Reviewer source
inspection. Jr owns tests, gates, records, and publication after source approval.
