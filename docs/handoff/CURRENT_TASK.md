# CURRENT_TASK

Ticket: DATA-007
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

DATA-007 — Free DEX/CEX Source Capability & Rate-Limit Probe.

REVIEW-0233 corrections applied. Five probes now route the supplied mock through
live paths; network guard prevents bare httpx.Client construction in tests.
33 DATA-007 tests pass, Ruff clean, repo control PASS.

## Evidence

- `tickets/DATA-007.md`
- `docs/reviews/REVIEW-0233_DATA-007_REOPENED_CHANGES_REQUIRED.md`
- `src/cryptofactors/acquisition/free_source_probes.py`
- `tests/acquisition/test_free_source_probes.py`
