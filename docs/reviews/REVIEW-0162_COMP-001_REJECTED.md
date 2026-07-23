# REVIEW-0162: COMP-001 — REJECTED

**Date:** 2026-07-22
**Reviewer:** DeepSeek V4 Pro
**Ticket:** COMP-001 — Simple Composites (Experiment #20)
**Status:** REJECTED
**Next required actor:** Sr Dev (corrections)

## Findings

### P1 — Composite direction inverted

`composite.py:160-176` assigns rank 1 to the best instrument, then uses
average rank directly as `score`. Downstream portfolio logic sorts scores
descending (higher-is-better), so it will long the worst composite ranks.
`score` should be `-avg_rank` (or `1/avg_rank`); `raw_value` may remain
`avg_rank`.

### P2 — Duplicate child factors create implicit unequal weighting

`composite.py:102-120` accepts arbitrary factors with no duplicate check.
Passing the same factor twice gives it 2× weight. Reject duplicate
`factor_id`s, or enforce the intended child set.

### Testing gap

Integration test (`test_composite_factors.py:175-248`) only checks finite
output. It does not verify that the best instrument is ranked highest
(higher-score-is-better) — regression risk for P1 after fix.

## Corrected source must

1. Invert score so higher = better (descending-sort convention).
2. Reject duplicate child factor_ids.
3. Add test assertion that best instrument has highest score.
