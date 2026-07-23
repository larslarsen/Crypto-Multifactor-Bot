# REVIEW-0204 — EXP-008 ACCEPTED (false discovery)

**Ticket:** EXP-008 — Multiple-Testing Risk Quantification for TSMOM Grid  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  

## Summary

The 14-config TSMOM grid winner (`tsmom_14_3`, +16.70%) was tested with four multiple-testing corrections:

| Method | p/q-value | Survives α=0.05? |
|--------|-----------|-------------------|
| Bonferroni | 1.0 | No |
| Benjamini-Hochberg | q=0.87 | No |
| White's Reality Check | p=0.85 | No |
| Hansen SPA | p=0.85 | No |

**Conclusion: `survives_correction: false`.** The candidate is a false discovery driven by selection from 14 configs. All four methods agree.

## Implications

1. **tsmom_14_3 is archived as a false discovery.** The PROMO-003 PAPER_APPROVED state is superseded and must not be used for any live decision.
2. The 2024-01 → 2026-07 dataset is **statistically spent** — every period was used in the grid selection process. No valid confirmatory test remains on this data.
3. **New research must use a pre-registered single-hypothesis framework** with a reserved holdout period that is never touched during exploration.

## Verifications

- ✅ `28_MULTIPLE_TESTING_ANALYSIS.json` — present, four methods, clear `survives_correction: false`
- ✅ pytest — 100% PASS
- ✅ ruff — ALL CHECKS PASSED

## Next

Authorizing **ARCH-001**: archive the false-discovery candidate and establish a pre-registered single-test research methodology for the next factor.
