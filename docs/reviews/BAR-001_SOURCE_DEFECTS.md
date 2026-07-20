# BAR-001 — Source defects found during Jr integration

**Ticket:** BAR-001
**Found by:** Jr Dev - Hermes
**Date:** 2026-07-20

## REVIEW-0031 / REVIEW-0032 contract mismatch — REJECTED/QUARANTINED source quality paths

**Requirement:** The integration contract requires published regression coverage for
`REJECTED` and `QUARANTINED` source quality gates, with the canonical publisher
producing an appropriate plan/status rather than hard-failing.

**Observed:** `_load_verified_bars` in `src/cryptofactors/market/bars.py` raises
`ValueError` when `quality_status` is `QualityStatus.REJECTED` or
`QualityStatus.QUARANTINED`, before any canonical plan is created.

**Impact:** Jr integration cannot construct valid tests for these gates without
bypassing the loader, which would make the test a fiction rather than an actual
behavioral check.

**Next:** Reviewer/routing decision: either revise the integration contract to
accept this loader behavior, or add a Sr review/drop to change source behavior
so rejected/quarantined sources are accepted into a quarantine/rejected plan
state rather than aborting publish.
