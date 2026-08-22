# CEX-002 Storage-Sizing Ruff Failure Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `FAILED_TEST_SOURCE_LINT`; exact three-line Claude correction authorized  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; no sizing invocation occurred

## Reviewed execution

Hermes correctly integrated review 191 at commit
`e317f2714c94750cb4bd64450b8790a6b2fda5d3`, pushed it, and followed the stop rule.
The focused sizing suite passed all 74 collected cases in 2 seconds. Exact-path Ruff then
exited status 1 with three `F401` findings, so Hermes ran no control or sizing command.
Receipt 180 and the sizing-envelope tree remain absent.

Production and CLI remain accepted at review-184 hashes. The passing 44-function test path
is SHA-256 `585f20db0461ad92af7cf6b1d4143aa52c4dfdff5f2bbfa44e76d4f6334e9f96`.

## Finding

The sizing test import list contains exactly three unused direct imports:

- `SIZING_ROW_BATCH` at line 36; the test correctly uses
  `sizing.SIZING_ROW_BATCH` when monkeypatching the module;
- `family_coefficients` at line 48; and
- `verify_retained_sample` at line 64.

Repository-wide text inspection confirms each name occurs nowhere else as a direct test
binding. This is lint-only test source cleanup. No assertion, fixture, production, CLI,
financial semantic, or sizing behavior changes.

## Claude correction boundary

To conserve Spark's weekly allocation, Sr Dev - Claude Build using Claude Opus 5 is
authorized to edit only
`tests/acquisition/test_binance_usdm_harmonic_sizing.py` by deleting exactly those three
unused import lines. Claude must not read or revise any other portion of the file, change
any other byte, run any command, perform Git work, or edit a repository record. Preserve
exactly 44 `def test_` functions and return the corrected test SHA-256. Stop for reviewer
inspection.

Hermes remains unauthorized until that exact source inspection. No sizing invocation,
Gate-2 acceptance, bulk acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work is
authorized. Next ticket remains `NONE`.
