# CURRENT_TASK

Ticket: NULL-001
State: BLOCKED
Next required actor: Sr Dev (corrections required)
Next ticket authorized: NONE

NULL-001 source rejected (REVIEW-0151). P1 finding: test bypasses research substrate. P2 findings: contracts in wrong module, string universe treated as character sequence, scores change with universe.

Governing documents:
- tickets/NULL-001.md (BLOCKED)
- docs/reviews/REVIEW-0151_NULL-001_REJECTED.md
- docs/reviews/REVIEW-0150_UNIVERSE-001_REJECTED.md
- docs/reviews/REVIEW-0148_EXP-001_ACCEPTED.md

## Sr Dev Correction Prompt

```
Correct NULL-001 source per REVIEW-0151 findings.

P1 — Test bypasses research substrate:
- tests/test_null_factor.py:58-75 uses synthetic independent Gaussian returns directly, bypassing ASOF/LABEL/EXP.
- Rebuild test to exercise accepted research substrate (CatalogAsOfStore → AsOfLabelEngine → PurgedChronologicalSplitter → ExperimentBundle) or document why current synthetic approach is acceptable for this specific validation step.

P2 — Contracts in wrong module:
- src/cryptofactors/factors/null.py:50-78 defines FactorValue, FactorFrame, Factor protocol.
- Move to src/cryptofactors/factors/contract.py (neutral contract module).
- Update imports in null.py and tests.

P2 — String universe treated as character sequence:
- NullFactor.compute("btc", as_of) iterates string as instruments "b", "t", "c".
- Reject string/bytes universe inputs with clear error.

P2 — Scores change when universe changes:
- null.py:121-126 seeds PRNG with sorted unique universe.
- Consider per-instrument seeding if universe-stable scores required.

Files to modify:
- src/cryptofactors/factors/contract.py (new)
- src/cryptofactors/factors/null.py (updated)
- tests/test_null_factor.py (updated)

Acceptance:
1. All tests pass
2. ruff clean
3. mypy clean
4. check_repo_control.py PASS

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces corrected source, stops for Reviewer. No commits until Reviewer accepts.
