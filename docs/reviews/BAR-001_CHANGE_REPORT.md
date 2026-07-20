# BAR-001 — Integration Change Report

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Next reviewer:** Senior Dev — Hermes
**Date:** 2026-07-20

## Summary

BAR-001 v1/v2/v3/v4/v5 junior integration is complete. The REVIEW-0033 findings were
either corrected by matching the actual v5 source contract or recorded as a source
defect because the requested behavior is not implemented in the source.

## Actual integration test count

- Tests path: `tests/market/test_canonical_bars.py`
- Committed state at `530ac8f` and later
- Count: **16** focused regression tests

## Reviewed v5 source positions

- Transform version 5, schema 2 in source docstring and transform spec.
- Legacy test updated: v1 dataset-id recompute failure only; unsupported-identity
  assertion removed because that branch is unreachable.
- Identity/duplicate tests build valid manifests with recomputed `manifest_sha256`
  before submission.
- Coverage/quality_summary dual-evidence test validates source-receipt disagreement
  on both fields.
- Whitespace-only canonicalization test verifies identical `config_sha256` for
  `1m` and ` 1m `.
- Hash/size mismatch test catches local file tampering.
- Forgery test invalidates `manifest_sha256` explicitly, matching loader message.
- Missing required partition test hits the actual partition-required branch in
  `_agree_partition_meta`.
- `REJECTED` and `QUARANTINED` source-quality paths are tested against actual
  source behavior (`ValueError: source dataset quality_status must be PASS`).
  Desired planner-level acceptance is **not** reachable through the current
  source; recorded in `docs/reviews/BAR-001_SOURCE_DEFECTS.md`.
- Schema-variant classifier updated from impossible `coin_marginated` to
  reachable `coin_margined` missing-`base_asset_volume` rejection.

## Known deviations / documented defects

1. **REVIEW-0031 REJECTED/QUARANTINED planner behavior** — Source rejects before
   planning. Documented in `docs/reviews/BAR-001_SOURCE_DEFECTS.md` (committed).

## Ticket-exact gate results (fresh)

- Focused `tests/market/test_canonical_bars.py`: 16 tests pass
- `ruff check tests/market/test_canonical_bars.py`: All checks passed!
- Full suite: pass
- `python3 scripts/check_repo_control.py`: PASS

## Commit

- HEAD: `530ac8f`

**This work is complete pending reviewer inspection.** Do not merge before reviewer
confirms disposition.
