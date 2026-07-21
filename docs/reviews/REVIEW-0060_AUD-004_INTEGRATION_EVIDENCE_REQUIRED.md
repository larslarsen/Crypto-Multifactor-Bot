# REVIEW-0060 - AUD-004 INTEGRATION EVIDENCE REQUIRED

**Ticket:** AUD-004 - Native headerless support for the Binance archive precision comparator
**Status:** RESOLVED - superseded by REVIEW-0061
**Next required actor:** Sr Dev - Sandbox
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The approved production source remains accepted for integration, and the required fixture shapes
are present. Final AUD-004 acceptance is withheld for two integration-evidence defects.

## 1. Mandatory Full Suite Did Not Pass

`AUD-004_CHANGE_REPORT.md` records that `PYTHONPATH=src uv run pytest -q --tb=short` ended in setup
errors because `/tmp/crypto_source_audit` was absent. The handoff nevertheless states that all
acceptance gates pass. A mandatory gate cannot be represented as passing when it did not complete.

Run the full suite in the repository's supported Sprint-003 test environment without weakening,
skipping, or deselecting tests. Record exact output. If the environment cannot be provisioned,
record the exact blocker and keep the ticket blocked rather than claiming acceptance evidence.

## 2. Malformed-Rate Regression Does Not Assert The Decision

`test_headerless_short_first_row_counts_malformed` verifies the malformed count but never asserts
`supports_timestamp_precision_transition`. It therefore does not prove that
`max_malformed_rate` governs the comparison result as required by REVIEW-0059.

Assert acceptance when the observed malformed rate is within the configured limit and rejection
when the same sample exceeds a stricter limit. Preserve the valid-inference and malformed-count
assertions for both archives.

## Required Task

Jr Dev - Hermes owns the focused correction, gates, records, commit, and push under
`docs/reviews/AUD-004_JR_FINAL_EVIDENCE_TASK.md`.
