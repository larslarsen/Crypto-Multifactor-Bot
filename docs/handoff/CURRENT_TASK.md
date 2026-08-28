# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Implementation Dev - Codex Spark - exact review-328 fixture line
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Immediate state: Hermes integrated the exact ADR-0030 source/test files in commit `72aac89`.
The targeted suite ran once and only
`test_wrong_retained_byte_count_is_rejected_before_plan_publication` failed. Production is
correct: the fixture changed primary/physical bytes to `1` but did not change the newly
authenticated report-summary byte field, so validation stopped at that earlier inconsistency.
No real Gate-2 data was touched.

Spark must edit only `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`. In that one
test, after the two assignments to byte value `1`, set
`document["physical_inputs"]["retained_credit"]["report_summary"]["retained_verified_credit_bytes"] = 1`
using normal multiline formatting. Preserve everything else. Do not run commands/tests or use
Git. Return the test hash, line count, and test-function count.

Hermes integration/rerun, Ruff, source repair, old-store retirement, planning, acquisition,
replay, `verify`, later gates, and next-ticket work remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/328_CEX002_TARGETED_TEST_FIXTURE_FAILURE_AND_SPARK_CORRECTION.md`
