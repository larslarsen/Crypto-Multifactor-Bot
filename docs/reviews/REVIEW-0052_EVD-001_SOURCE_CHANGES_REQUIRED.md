# REVIEW-0052 - EVD-001 SOURCE CHANGES REQUIRED

**Ticket:** EVD-001 - Operational Evidence Registry
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY - RESOLVED (Sr drop integrated; EVD-001 ACCEPTED at REVIEW-0057_EVD-001_ACCEPTED.md)
**Next required actor:** Sr Dev - Grok Build
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

The implementation stays within the approved layer and does not implement experiment links, but
the source is not approved for Jr integration. Correct the findings below without changing schema,
migrations, research content, or ticket scope.

## 1. Evidence content identity is trusted rather than verified

`EvidenceRepository.add_evidence` stores caller-supplied `content_sha256` without deriving or
verifying it. The same ID/hash with changed metadata is also accepted as idempotent. This defeats
the ticket's deterministic immutable-content contract.

Define one canonical evidence body excluding the hash field, derive its hash with
`content_sha256`, reject a supplied mismatch, and compare complete canonical content for
idempotence. Never permit a caller-chosen digest to conceal changed content.

## 2. Decisions can cite unrelated snapshots and superseded decisions

`append_decision` verifies that the snapshot and hypothesis version each exist, but not that the
snapshot belongs to the decision's exact `(hypothesis_id, version)`. It also accepts a
`supersedes_decision_id` from another hypothesis/version, and allows `CORRECT`/`REOPEN` without a
superseded event.

Require exact snapshot ownership. Require `CORRECT` and `REOPEN` to reference a prior decision for
the same hypothesis/version; reject supersedes references on actions that do not correct/reopen.
Keep all changes append-only.

## 3. Point-in-time snapshot selection is not reliable

UTC strings omit fractional seconds when microseconds are zero. SQLite lexical comparison can
therefore order `...00Z` after `...00.123000Z`. Snapshot filtering also checks only link time, so a
backdated link can expose evidence whose `registered_at` is later than `as_of`.

Use one fixed-width canonical UTC representation for every persisted/comparison timestamp.
Snapshots may include only evidence and links registered by `as_of`; reject link registration
that predates its evidence registration. Preserve stable ordering and exact idempotence.

## 4. Seed import silently loses governing registry state

The real seed contains `lifecycle`, `verdict`, and additional provenance such as
`sprint_002_source_basis`; the importer silently drops them. It also mutates row-by-row, allowing a
late invalid entry to leave a partial seed.

Validate the complete seed before mutation and import atomically. Preserve every supported source
field deterministically: hypothesis details/provenance belong in validated immutable version
content, while lifecycle/verdict belong in deterministic append-only initial decision state.
Reject unknown unsupported fields rather than silently discarding them. Re-import must be fully
idempotent.

## 5. “Current-state” export is incomplete

The export omits unlinked evidence and most immutable hypothesis-version content, and lists event
history without deriving each hypothesis's current lifecycle/verdict. JSON and Markdown therefore
do not represent the registry's current state.

Include all registered evidence, complete immutable version identity/content, snapshots/links,
decision history, and deterministically derived latest lifecycle/verdict. Keep JSON byte-stable and
Markdown deterministic from the same canonical state.

## 6. Conflict and CLI failures are not consistently typed

- A slug collision on a different hypothesis can fall through to a raw SQLite FK error.
- Link idempotence ignores `registered_at` and `registered_by` despite claiming full identity.
- CLI payload read/JSON/model/time failures can escape as tracebacks instead of stable nonzero
  command errors.
- `build_snapshot(actor=...)` accepts but ignores audit identity; remove the unused argument unless
  it is represented by the existing schema.

Surface stable repository/CLI errors and require complete provenance equality for idempotence.

## Preserved behavior

Keep canonical hypothesis hashes, deterministic snapshot ordering/IDs, promotion guards, immutable
decision insertion, migration-0002 reuse, layer boundaries, and the explicit experiment-link
deferral. Schema and migration edits remain unauthorized.

## Stop condition

Sr edits production source only and returns the corrected source drop. No tests, records, Git,
commits, pushes, or gate claims. Jr integration remains unauthorized.
