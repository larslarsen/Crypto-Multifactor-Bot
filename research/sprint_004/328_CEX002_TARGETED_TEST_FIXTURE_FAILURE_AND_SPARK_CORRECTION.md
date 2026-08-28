# CEX-002 Targeted Test Fixture Failure and Spark Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** integrated production source retained; one mechanical test-fixture correction authorized
- **Authorized actor:** Implementation Dev - Codex Spark, GPT-5.3-Codex-Spark High
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Failure review

Hermes integrated and pushed the exact review-326 source/test files in commit
`72aac89a5d2495513531b5b9ded4a2a514986bfb`. The integrated hashes remain:

- acquisition source
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`;
- acquisition test
  `19165d4e5d3fef565f4f35c41c7bf82322ad60eaa453dcd97cd41ef93354ed96`;
  and
- unchanged CLI
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`.

The targeted acquisition suite ran once and stopped with one failed test:

```text
FAILED tests/acquisition/test_binance_usdm_harmonic_acquisition.py::test_wrong_retained_byte_count_is_rejected_before_plan_publication
```

The failure is a test-fixture sequencing defect, not a production defect. The test changes
`physical_inputs.retained_credit.bytes` and `physical_inputs.retained_credit_bytes` to `1` but
leaves `physical_inputs.retained_credit.report_summary.retained_verified_credit_bytes` at the
original value. The complete review-325 production validator correctly rejects that internal
report-summary inconsistency before the test reaches its intended mismatch against
`AuthorityPins.retained_credit_bytes`.

## Exact Spark correction

Spark may edit only:

- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Inside `test_wrong_retained_byte_count_is_rejected_before_plan_publication`, immediately after
the two existing assignments which set the primary and physical retained byte counts to `1`,
add exactly this third fixture assignment:

```python
document["physical_inputs"]["retained_credit"]["report_summary"][
    "retained_verified_credit_bytes"
] = 1
```

Preserve the existing `pytest.raises(..., match="retained credit bytes changed")` assertion and
every other byte. Do not change production source, helpers, other tests, CLI, governance,
configuration, or data. Do not run commands/tests and do not use Git.

Return once with the test-file SHA-256, line count, test-function count, and confirmation that
only the authorized test file changed.

Hermes integration and the one remaining targeted rerun await reviewer inspection. Ruff,
source repair, full-suite/repository validation, control, old-store retirement, corrected
planning, acquisition, replay, `verify`, Gate 3, normalization, catalog, NautilusTrader,
Harmonic Trader, experiments, PAPER/LIVE, and next-ticket work remain unauthorized. Gate 2
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
