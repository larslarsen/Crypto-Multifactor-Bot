# REVIEW-0169 — PROMO-001 Accepted

**Ticket:** PROMO-001 (Explicit Paper Promotion, Sequence #23)
**Status:** ACCEPTED

Promotion Registry implementation accepted: `PromotionRegistry` (SQLite backend), `PromotionIdentityPayload`, state machine with transition DAG and hard gates (`PAPER_APPROVED` requires evidence reference, `LIVE_APPROVED` requires owner authority + paper observation). Serving discovery via `get_active_promoted_artifact` fails closed. 6 tests pass.

**Gate results:**
- pytest: 6/6 pass
- ruff: All checks passed
- mypy: clean
- check_repo_control: PASS

**Next:** Next sequence ticket or architecture decision.
