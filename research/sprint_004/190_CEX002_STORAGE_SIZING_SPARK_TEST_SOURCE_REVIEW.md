# CEX-002 Storage-Sizing Spark Test Source Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `REJECTED`; final mechanical Spark correction authorized  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; no sizing invocation occurred

## Reviewed drop

Spark changed only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`. The reviewed
SHA-256 is
`ee556f77d860bc9c439221254203143d6baffbc5d36ef468f57e9430d5651aaa`, with 44
`def test_` functions. Production and CLI remain byte-identical at their review-184
hashes.

The one-non-consumable-row-per-family cohort is semantically correct and avoids overlap
with retained-credit rows. The arithmetic scan is now limited to the intended helpers,
and the content-addressed envelope symlink test accepts the two fail-closed refusal paths.
Four small test-source residuals must be corrected before another Hermes execution.

## Findings

1. The end-to-end receipt test still reads nonexistent
   `counts["coinalyze_receipts"]`. Production and the later exact Coinalyze equation test
   correctly use `counts["projected_coinalyze_receipts"]`; use that real field here too.
2. The restricted arithmetic scan still skips any line containing `float(`, so it would
   ignore rather than reject the condition it claims to guard. Assert `"float(" not in
   source` once, and skip only comments while checking for ordinary arithmetic `/` in the
   two helper sources.
3. Spark broadened two symlink regexes outside review 189: the receipt-publication test and
   prior-receipt-read test. Restore their prior expectations. Only
   `test_publication_refuses_a_symlink_swapped_after_the_check` needed the alternative
   `escapes its evidence root` result.
4. Wrap the new cohort generator and retained envelope regex to the repository's
   100-column style before Hermes reaches exact-path lint.

## Correction boundary

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized to edit
only `tests/acquisition/test_binance_usdm_harmonic_sizing.py` for the four exact changes
above. Preserve the corrected 12-family non-consumable cohort, dynamic beyond-`2**53`
assertions, the intended envelope-symlink alternative, every other byte, and exactly 44
test functions.

Spark runs no test, linter, control, Git, network, sizing, or data command, changes no
production/CLI byte or repository record, returns the corrected test SHA-256, and stops
for reviewer inspection. Hermes remains unauthorized until that inspection.

No sizing invocation, Gate-2 acceptance, bulk acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source,
reduced-scope, or next-ticket work is authorized. Next ticket remains `NONE`.
