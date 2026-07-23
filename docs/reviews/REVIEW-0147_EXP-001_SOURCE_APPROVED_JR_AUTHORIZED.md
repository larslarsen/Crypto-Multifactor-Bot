# REVIEW-0147 — EXP-001 SOURCE APPROVED / JR INTEGRATION AUTHORIZED

**Ticket:** EXP-001 — Experiment Bundles & Fingerprints
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev — Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-22

## Decision

EXP-001 corrected Sr source drop is approved for integration.

- `src/cryptofactors/validation/experiment.py` (167 lines) implements `ExperimentBundle` (frozen/slots), `ExperimentRegistry` (Protocol), `InMemoryExperimentRegistry`.
- P1-1: `register()` recomputes fingerprint and rejects tampered bundles.
- P1-2: `factor_defs` entries and `metadata` keys must be `str`; non-strings rejected.
- Deterministic SHA-256 fingerprint via canonical serialization.
- Fail-closed on missing bundles, duplicates, invalid types.

## Jr authorization

Jr Dev — Hermes owns:
1. Tests covering fingerprint tampering (tamper → ExperimentError), non-string factor IDs, non-string metadata keys, register/duplicate/load/list/has.
2. Run acceptance gates (pytest on validation, ruff, mypy, repo-control).
3. Record results in change report.
4. Update ticket/backlog/README/handoff/CURRENT_TASK to AWAITING_REVIEW.
5. Commit and push.

No reviewer acceptance claim. No next ticket. Stop after push.
