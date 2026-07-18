# Crypto Multifactor Bot

Cross-sectional cryptocurrency multifactor research program.

## Architecture is frozen (RFC-001)

The v1 system architecture is **frozen as RFC-001** and any change to it
requires a new Architecture Decision Record. See
[`docs/ARCHITECTURE_RFC.md`](docs/ARCHITECTURE_RFC.md) and the ADR set under
[`docs/architecture/adr/`](docs/architecture/adr/) (indexed in
[`adr/README.md`](docs/architecture/adr/README.md)). Implementation proceeds
against the frozen architecture; an architecture-doc change without a
corresponding ADR is rejected in review.

## Layout

- `src/cryptofactors/` — installable package (ids, contracts, cli); `cf` command.
- `docs/architecture/` — the v1 system architecture (11 docs) + `adr/` (ADRs
  0001–0007, including the freeze ADR-0007).
- `research/sprint_001/` — the Sprint 1 research specification package
  (charter, legacy audit, PIT/universe/validation contracts, factor cards,
  volume-bar replication protocol, literature synthesis, experiment registry,
  architecture handoff). See
  [`research/sprint_001/README.md`](research/sprint_001/README.md).
- `schemas/`, `configs/`, `sql/` — typed manifests, example configs, SQLite
  control schema + analytics views.
- `tests/` — scaffold tests (run with `uv run pytest`).

## Evidence status — READ THIS

Per the sprint README, the following holds and is **intentionally** so:

- **Raw observations and full prediction lineage are unavailable** in this
  public repository. Dataset counts and date spans are recorded as **author
  claims**, not verified results.
- **No historical performance claim is accepted as validated.**
- The **information-bar result is a replication candidate, not an established
  edge.**
- The **committed information-bar models are quarantined** from serving until
  causal-representation and parity tests pass.

### Audit interpretation (senior + junior review)

| Dimension | Status |
|---|---|
| Disclosure / internal consistency | Pass |
| Artifact reproducibility | Not established |
| Validation quality | Unresolved — evaluation defects identified (noncausal thresholding, train/test overlap, evaluator/trainer mismatch, cross-venue parity) |
| Serving readiness | Blocked, as intended |
| Evidence status | Quarantined hypothesis, not accepted alpha |

Documenting these caveats does **not** fix the underlying evaluation defects.
It means the repository is not misleading readers into treating the artifacts
as production-ready. Architecture and implementation should begin only after
the Tier-0 data acceptance gates pass (see
`research/sprint_001/02_DATA_AUDIT_PLAN.md`).

## Legacy context

The research program treats `https://github.com/larslarsen/Trading-Bot` as an
evidence archive and a source of potentially reusable components — **not** as
the architecture or research design to preserve.
