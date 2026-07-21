# REVIEW-0067 - AUD-005 SOURCE TYPE CORRECTION REQUIRED

**Ticket:** AUD-005 - Provider-candle comparison by explicit comparable dimensions
**Status:** RESOLVED - CORRECTED AND APPROVED BY REVIEW-0068
**Next required actor:** Reviewer
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The local source correctly implements partial provider views, deterministic comparison metadata,
historical default behavior, corrected Binance indexes, semantic trade-count exclusion, and real
structured runner output. Source approval is withheld for one typed-API defect.

`comparable_dimensions` is annotated as `Sequence[str]`, which excludes an actual `set[str]` for
static callers even though AUD-005 requires an explicit set of dimensions. `_resolve_comparable_dimensions`
also coerces each item with `str(raw)`, allowing non-string objects whose string representation
matches a dimension to bypass the intended type contract.

## Required Correction

- Accept a typed string collection that includes sets, lists, and tuples.
- Reject scalar strings/bytes as the collection itself.
- Reject non-string members without coercion.
- Preserve empty, unknown, and duplicate rejection plus canonical output ordering.
- Preserve every other REVIEW-0066 source behavior unchanged.

The local source assignment is `docs/reviews/AUD-005_SR_SOURCE_CORRECTION_TASK.md`.

**Resolution:** The type-collection correction was completed, the source was approved under
REVIEW-0068 and integrated under REVIEW-0069. AUD-005 is closed.
