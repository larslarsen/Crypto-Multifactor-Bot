# AUD-004 — Change Report: native headerless support for Binance precision comparator

**Ticket:** AUD-004
**State:** BLOCKED
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Source/behavior contract
Production source already uses max observed width across sampled rows in headerless mode.
No production-source changes in this Jr evidence cycle.

## Current blocker: Sprint-003 test environment unavailable
The required full-suite gate `PYTHONPATH=src uv run pytest -q --tb=short` cannot complete
in this environment. Exact failure evidence:

1. Staging directory exists: `/tmp/crypto_source_audit`
2. Runner import fails:
   `ModuleNotFoundError: No module named 'httpx'`
   Dependency is declared in `pyproject.toml` but not installed in the active runtime.
3. When runner is invoked with system Python, it fails at runtime:
   `source_audit.errors.SerializationError: float is not supported; use Decimal for numeric values | context={'value': '0.1'}`
   This is a production-source serialization defect in `src/source_audit/serialization.py`,
   not an AUD-004 test/evidence issue. Jr Dev does not edit production source per repo policy.

## Remediation path
- Install declared dependencies in the repository-supported runtime.
- Fix `SerializationError` in production source via Sr/Reviewer authorization.
- Re-run full suite and record exact output.

## What did pass
- Focused precision tests: 12 passed
- Ruff on `src/source_audit tests/test_binance_precision.py`: All checks passed
- Mypy on `src/source_audit tests/test_binance_precision.py`: Success: no issues
- Repo control: PASS
