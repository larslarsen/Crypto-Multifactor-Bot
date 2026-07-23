# REVIEW-0163: COMP-001 Round 2 — REJECTED

**Date:** 2026-07-22
**Reviewer:** DeepSeek V4 Pro
**Ticket:** COMP-001 — Simple Composites (Experiment #20)
**Status:** REJECTED
**Next required actor:** Sr Dev (corrections)

## Changes Verified

- P1 (score direction): `score=-avg_rank` — correct.
- P2 (duplicate factor_ids): rejected in constructor — correct.

## Remaining Finding

### P1 — Integration test rank assertion is tautological

`test_composite_factors.py:244-247`:
```python
top_iid = max(scores, key=scores.__getitem__)
assert scores[top_iid] == max(scores.values())
```
This computes `top_iid` via `max(scores)` then asserts its score equals
`max(scores)`. The assertion is tautological — it cannot detect inverted
ranking because `top_iid` is already the max-scoring instrument.

**Fix:** Identify the expected best instrument independently (e.g. by `raw_value`
or by known seed) and assert that it has the highest `score`. Example:
```python
scores = {v.instrument_id: v.score for v in frame.values}
raws = {v.instrument_id: v.raw_value for v in frame.values}
best = min(raws, key=raws.__getitem__)
assert scores[best] == max(scores.values())
```

## Corrected source must

1. Fix integration test rank assertion (tautology → independent check).
