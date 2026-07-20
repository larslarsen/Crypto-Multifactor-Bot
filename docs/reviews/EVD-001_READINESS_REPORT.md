# EVD-001 — Readiness Report (Jr Records-Only Audit)

**Ticket:** EVD-001 - Operational Evidence Registry
**Actor:** Jr Dev - Hermes (records/analysis only)
**Date:** 2026-07-20
**Scope:** Resolve the undefined `experiment identity contract` dependency and convert the
ticket's broad deliverables into a reviewable implementation contract. No production source,
tests, migrations, schemas, architecture decisions, or research content are created or modified
by this report. Missing contracts are identified explicitly; none are inferred.

---

## 1. Authoritative identity & versioning rules already present

Source of truth: `src/cryptofactors/evidence/models.py`, `src/cryptofactors/evidence/repository.py`,
`sql/migrations/0002_evidence_registry.sql`, `sql/migrations/0001_baseline.sql`.

- **Hypothesis identity:** `HypothesisVersion.hypothesis_id` is regex-constrained
  `^H-[0-9]{3,}$` (models.py:81). The DB `hypothesis` table uses it as `PRIMARY KEY`.
- **Versioning / immutability:** `hypothesis_version` has composite PK
  `(hypothesis_id, version)` with `version >= 1` (migration 0002:10-27). Each version carries a
  `content_sha256 TEXT NOT NULL UNIQUE` (migration 0002:22) — so a version is content-addressed
  and immutable; a new edit requires a new `(hypothesis_id, version)` row. This is the
  append-only hypothesis-version contract.
- **Evidence identity:** `EvidenceItem.evidence_id` is regex-constrained `^EV-[A-Z0-9-]+$`
  (models.py:105) and `content_sha256` is `^[a-f0-9]{64}$` UNIQUE (models.py:114). Evidence is
  therefore content-addressed and immutable per row.
- **Decision events:** `hypothesis_decision_event` is an append-only event log keyed by
  `decision_id` PK, with `action`, `lifecycle`, `verdict` enums, an `evidence_snapshot_id`
  FK, and an optional `supersedes_decision_id` self-reference (migration 0002:85-102). Lifecycle
  and verdict enums are mirrored in `models.py` (`HypothesisLifecycle`, `HypothesisVerdict`).
- **Link integrity:** `hypothesis_evidence_link` and `hypothesis_experiment_link` enforce
  direction/relevance/role enums and FK back to `hypothesis_version` (migration 0002:46-70).
- **Snapshot identity:** `evidence_snapshot` is keyed by `snapshot_id` PK with a UNIQUE
  `content_sha256` (migration 0002:72-83).

**Resolved at the identity/versioning level:** hypothesis + evidence content-addressed
immutability, append-only decisions, and link/snapshot identity are already specified in the
schema and the pydantic models. The "identity contract" for hypotheses and evidence is
therefore *already present*; what is undefined is the *experiment identity* leg (see §6).

---

## 2. Migration-0002 tables, constraints, and invariants

Tables (all `IF NOT EXISTS`, FK `PRAGMA foreign_keys = ON`):

| Table | Key | Notable constraints / invariants |
|---|---|---|
| `hypothesis` | PK `hypothesis_id` | `slug` UNIQUE, `created_at`, `created_by` |
| `hypothesis_version` | PK `(hypothesis_id, version)` | `version >= 1`; `content_sha256` UNIQUE; all text fields NOT NULL |
| `evidence_item` | PK `evidence_id` | `kind` CHECK IN (7 values); `content_sha256` UNIQUE; `metadata_json` |
| `hypothesis_evidence_link` | PK `(hypothesis_id, version, evidence_id)` | `direction`/`relevance` CHECK; `integrity_json`; FK to `hypothesis_version` |
| `hypothesis_experiment_link` | PK `(hypothesis_id, version, experiment_fingerprint, role)` | FK to `experiment_spec(fingerprint)` |
| `evidence_snapshot` | PK `snapshot_id` | UNIQUE `content_sha256`; FK to `hypothesis_version` |
| `hypothesis_decision_event` | PK `decision_id` | `action`/`lifecycle`/`verdict` CHECK; FK to `evidence_snapshot`; self `supersedes` FK |

Indexes: `idx_hypothesis_version_created`, `idx_evidence_kind_registered`,
`idx_evidence_link_hypothesis`, `idx_hypothesis_decision_time`.

**Invariants available to the implementation:**
- Referential: every link/snapshot/decision must reference an existing `(hypothesis_id, version)`
  and (for experiments) an existing `experiment_spec(fingerprint)`.
- Content integrity: duplicate `content_sha256` is rejected at the DB level (UNIQUE), enforcing
  immutability of hypothesis versions and evidence items.
- Decision provenance: every `SET_VERDICT`/`SUPPORTED`/`REPLICATED` decision must cite a real
  `evidence_snapshot_id`.

The ticket's stated invariant — "No `SUPPORTED`/`REPLICATED` decision may reference a snapshot
containing only literature or legacy results; evidence with causal/point-in-time integrity `FAIL`
cannot support promotion" — is **not yet enforced by any DB constraint or code**. It is a
*semantic invariant the implementation must enforce in the service layer* (it can read
`evidence_item.kind` and `EvidenceIntegrity` grades from the link's `integrity_json`). This is a
required implementation rule, not a present contract.

---

## 3. Proposed minimal module/API and CLI surface (matching conventions)

Layer rule (`scripts/check_layer_imports.py`): `evidence` may import only `core` and `catalog`.
The implementation must stay inside `src/cryptofactors/evidence/` and must not reach into
`experiments`, `market`, `factors`, etc.

Existing repository already provides (repository.py): `register_hypothesis`, `add_evidence`,
`append_decision`. The readiness proposal extends — does not replace — this surface:

- `EvidenceRepository.build_snapshot(hypothesis_id, version, *, as_of) -> EvidenceSnapshot`
  (assemble link + integrity state into a deterministic `snapshot_json`, hash via
  `canonical.content_sha256`, persist to `evidence_snapshot`). *Not present today.*
- `EvidenceRepository.export_current_state(format: "markdown" | "json") -> str`
  (render registered hypotheses/versions/decisions from the snapshot; deterministic via
  `canonical_json_bytes`). *Not present today.*
- `seed_import_hypotheses(path: Path, *, actor) -> int` (load
  `research/evidence/hypotheses.yaml` into `hypothesis`/`hypothesis_version` using the existing
  `register_hypothesis` path; skip duplicates by `content_sha256`). *Not present today.*

CLI surface (follow `src/cryptofactors/cli.py` Typer convention; add an `evidence_app` sub-typer
like the existing `catalog_app`):
- `evidence register-hypothesis ...`, `evidence add-evidence ...`, `evidence decide ...`,
  `evidence snapshot ...`, `evidence export --format md|json`, `evidence seed --yaml
  research/evidence/hypotheses.yaml`.

These are **proposals for reviewer authorization** — this audit creates none of them.

---

## 4. Deterministic hash, append-only decision, snapshot, export, seed-import contracts

- **Hash contract (present):** `canonical.canonical_json_bytes` (deterministic
  `sort_keys`, `allow_nan=False`, `ensure_ascii=False`) + `canonical.content_sha256` is the
  single authoritative hashing primitive. Every `content_sha256` in the schema is produced by
  this. New snapshot/export code must reuse it — no ad-hoc hashing.
- **Append-only decision contract (present):** decisions are insert-only events; corrections use
  `action=CORRECT`/`REOPEN` with `supersedes_decision_id` rather than UPDATE. The model
  (`HypothesisDecision`) already enforces this shape.
- **Snapshot contract (proposed):** `snapshot_json` is the canonical JSON of the linked
  evidence state at `as_of`; `content_sha256` is its `canonical.content_sha256`. Identical state
  yields identical hash (idempotent / de-duplicated by UNIQUE).
- **Export contract (proposed):** Markdown/JSON current-state report is a pure function of the
  latest snapshot; JSON export is `canonical_json_bytes` of the same structure (byte-stable).
- **Seed-import contract (proposed):** `research/evidence/hypotheses.yaml` (registry v2,
  `research/evidence/README.md`) is the seed source; import maps each entry to
  `HypothesisVersion` and registers via the existing path; rows whose `content_sha256` already
  exists are skipped (idempotent). No YAML entry may invent fields outside the
  `HypothesisVersion` model.

---

## 5. Acceptance-test matrix and exact ordered acceptance commands

All below run *after* the (separately authorized) Sr production implementation; this report does
not execute them.

| # | Test case | Expected |
|---|---|---|
| 1 | Register hypothesis v1, then v2 with changed text | two rows; distinct `content_sha256`; no UPDATE |
| 2 | Re-register identical v1 payload | rejected/ skipped on UNIQUE `content_sha256` |
| 3 | Add evidence with `EV-` id + 64-hex sha | row persists; bad id/sha rejected by model |
| 4 | `SET_VERDICT=SUPPORTED` citing snapshot of only `LITERATURE_PUBLISHED` | rejected by semantic invariant |
| 5 | `SET_VERDICT=SUPPORTED` where link `integrity_json` has `point_in_time=FAIL` | rejected |
| 6 | `build_snapshot` twice for same state | same `snapshot_id`/`content_sha256` |
| 7 | `export_current_state("json")` byte-stable across runs | identical bytes |
| 8 | `seed_import_hypotheses` then re-run | idempotent (no duplicate rows) |
| 9 | Decision `CORRECT` with `supersedes_decision_id` | append-only; original retained |

Exact ordered commands (mirrors prior tickets' style):
1. `PYTHONPATH=src uv run pytest tests/evidence -q --tb=short`
2. `PYTHONPATH=src uv run ruff check src/cryptofactors/evidence tests/evidence`
3. `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/evidence tests/evidence`
4. `PYTHONPATH=src uv run pytest -q --tb=short`
5. `python3 scripts/check_layer_imports.py`
6. `python3 scripts/check_repo_control.py`

---

## 6. Layer/import boundaries, excluded scope, security risks, recommendation

- **Boundaries:** `evidence` → {`core`, `catalog`} only. The implementation must not import
  `experiments`, `market`, `factors`, `validation`, etc. `experiment_spec` is referenced by FK
  but lives in the `experiments` layer (0001 baseline / control_schema.sql) — EVD-001 must
  *consume* that FK, not create it.
- **Unresolved dependency (the undefined "experiment identity contract"):** EVD-001's schema
  links hypotheses to `experiment_spec(fingerprint)`, but the `experiment_spec` identity/version
  contract (how fingerprints are computed, what constitutes a valid spec) is owned by the
  **experiments** layer, which is not yet implemented. The readiness recommendation is to treat
  `experiment_spec` as an external dependency with a stable `fingerprint TEXT` interface and to
  **block Sr production work on EVD-001's experiment-link deliverable** until the experiments
  layer defines that contract. Hypothesis/evidence identity (§1) is ready now.
- **Excluded scope (per ticket):** no performance/score aggregation; no research content; no new
  migrations or schema changes (0002 already provides the schema); no architecture decisions.
- **Security risks:** (a) `metadata_json` / `integrity_json` are free-text JSON — the service
  layer must validate structure before insert to avoid malformed-state snapshots. (b) Seed import
  reads a repo file (`research/evidence/hypotheses.yaml`) — must be treated as data, never as
  code; no `eval`/`exec`. (c) `registered_by`/`actor` are audit fields — must come from an
  authenticated caller, not be caller-supplied spoofable identity in a serving context.
- **Recommendation:** **Authorize Sr production-source work for the hypothesis/evidence/snapshot/
  export/seed deliverables (§3-§4) now**, because their identity, hashing, and storage contracts
  are already present and self-contained within the `evidence` layer. **Block** the
  `hypothesis_experiment_link` deliverable until the experiments layer specifies the
  `experiment_spec` fingerprint contract. The implementation is otherwise ready to proceed.

---

## Status of this report

Records/analysis only. No source, test, migration, schema, or architecture artifact was created
or modified. Next required actor: Reviewer. Next ticket authorized: NONE.
