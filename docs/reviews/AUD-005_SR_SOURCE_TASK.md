# AUD-005 - SR PRODUCTION SOURCE TASK

**Ticket:** `tickets/AUD-005.md`
**Actor:** Sr Dev - Sandbox
**Status:** AUTHORIZED AFTER CONTROL PUBLICATION - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Implement the REVIEW-0066 comparable-dimension contract in the existing source-audit layer and
Sprint-003 runner.

## Required Behavior

- Add a typed explicit comparable-dimension API to `compare_bars` and deterministic comparison
  metadata to `BarComparisonResult`.
- Preserve all-dimensions-required historical behavior when the new argument is omitted.
- Require selected mapping fields; tolerate absent unselected fields; reject unknown or empty
  selections.
- Keep timestamp alignment, missing intervals, duplicates, Decimal tolerances, and mismatch signs
  unchanged.
- Do not weaken `OHLCVBar` by making reconstructed fields optional; use a private comparison shape
  if needed for provider mappings.
- Update the Sprint-003 runner to use Binance kline quote volume index 7, explicitly exclude trade
  count, preserve column-8 trade-count semantics as non-comparable, and emit the structured result.
- Never equate or relabel aggTrades record count as provider raw-trade count.

## Source Scope

Production/source files only under `src/source_audit/` and
`scripts/audit/run_sprint003_audit.py`. Reviewer inspects the local source drop; Jr Dev - Hermes
owns subsequent tests, research/evidence corrections, integration, records, commit, and push.

## Completion Condition

Complete the minimal local source implementation for reviewer inspection.
