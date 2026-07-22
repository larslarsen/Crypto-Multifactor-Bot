# REVIEW-0112 — FX-003 CHANGES REQUIRED

**Reviewed commit:** c1153d146c57dbaf55b03621d915ed44bce11ea4
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Corrections required
1. Use actual Drive file ID `1ptNqWYidLkhb2VAKuLCxmp2OXEfGO-AP`; do not use `id=Kraken_OHLCVT`.
   Register the warning/confirmation flow and exact ranges where retained.
2. Correct CSV facts: headerless; 3,200 rows; 2017-03-29 through 2025-12-31;
   interval 24 hours; May 12 2022: O=.9953 H=.9989 L=.92 C=.9971. G02 PASS.
3. Register retained Kraken support article body/headers and quarterly-folder body/headers.
   Record current quarters Q1-2023 through Q1-2026.
4. Correct ZIP64 facts: local-header offset 6080252262 was captured; local header is 88 bytes;
   compressed data starts 6080252350; R02's 200 bytes contain header plus 112 compressed bytes.
5. Correct gates: G01 PASS, G02 PASS, G03 FAIL_PARTIAL, G04 FAIL_PARTIAL, G05 FAIL_PARTIAL,
   G06 PASS, G07 FAIL_CONFLICT, G08 FAIL_PARTIAL. Blocking: G03, G04, G05, G07, G08.
6. Licensing: support page permits download/use in code/conversion; EEA Terms restrict copying
   and automated extraction. Fail on unresolved applicability.
7. Correct Last-Modified fields from retained headers; state six registered header rows.
8. Validate paths/hashes/sizes, final statuses, inflated SHA/CRC/rows/bounds, repo control, git diff.

**Disposition:** All corrections applied and committed at `57915326c804088c22e61ba4adcb4d113bdf756c`.
