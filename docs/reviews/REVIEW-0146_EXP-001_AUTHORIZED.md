# REVIEW-0146 — EXP-001 AUTHORIZED (Experiment Bundles & Fingerprints)

**Authorized ticket:** EXP-001
**Priority:** P0 (research substrate)
**Gate role:** BLOCKING_FOR_RESEARCH_SUBSTRATE
**Date:** 2026-07-22
**Next required actor:** Sr Dev (source) then Jr Dev (integration)

## Authorization

After ASOF-001, SPLIT-001, and LABEL-001 acceptance, authorize the experiment-bundle infrastructure (Implementation Sequence #16).

This is unblocked: as-of access, purged splits, and labels are all accepted. Costed portfolio simulation (#15) is deferred — it requires survivorship-free universe snapshots (blocked by DF-08). Experiment bundles provide the reproducibility scaffold needed to preregister and fingerprint experiments independent of universe construction.

Objective: Define a reviewed `ExperimentBundle` protocol with deterministic SHA-256 fingerprints and a registry for validation, deduplication, and retrieval. Same inputs → same fingerprint → reproducible research record.

## Required Contract
- `ExperimentBundle` immutably groups label config, split config, factor identifiers, and metadata.
- Deterministic SHA-256 fingerprint from canonical serialization.
- `ExperimentBundleRegistry` validates fingerprints, registers bundles, detects duplicates, loads by fingerprint, lists all registered bundles.
- Fail-closed on corrupt/missing bundles.
- Factor identifiers are opaque strings (factor materialization out of scope).

## Scope
- New module under `src/cryptofactors/validation/` (e.g. `experiment.py`).
- Protocol + concrete implementation.
- Uses no new data sources.

## Out of Scope
- Factor materialization, portfolio simulation, universe construction.
- Backend persistence choice, CLI, live serving.
- New data sources.

## Next
1. Jr creates ticket + governance.
2. Sr produces source drop. Stop for reviewer.
3. Jr integrates + tests + gates. AWAITING_REVIEW.
4. No next ticket authorized.
