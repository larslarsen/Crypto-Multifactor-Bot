# Sr Dev Prompt — EXP-001 Correction

**Model:** Grok 4.5 (Grok Build)
**Role:** Sr Dev
**Ticket:** EXP-001
**Base:** prior experiment.py drop (145 lines)

---

CORRECT these two P1 issues in src/cryptofactors/validation/experiment.py:

## P1-1: Registry must verify recomputed fingerprint

In register(), after accepting an ExperimentBundle, recompute the fingerprint from
_canonical_bytes() and compare against the stored fingerprint. If they don't match,
raise ExperimentError. Do not trust the bundle's fingerprint field.

## P1-2: Reject non-string factor IDs and metadata keys

In ExperimentBundle.__post_init__, raise ExperimentError if any element in factor_defs
is not a str, or if any metadata key is not a str. Do not silently convert via str().

## Rules

- No other changes.
- No tests, no commits, no pushes.
- Return only the corrected experiment.py.
