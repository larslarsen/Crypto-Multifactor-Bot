# REVIEW-0116 — REF-003 CHANGES REQUIRED

**Reviewed commit:** 503e7d85629c02b1941aab01538cf48a6dcf1f02
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Findings
1. Evidence provenance was wrong. The legal-terms listing was reused with an unsupported
   `api2.bybit.com/fiat/order/legal/terms` URL and the same request was duplicated across
   R01/R03 (identical bytes/headers while claiming different requests).
2. Document identities must derive from the retained JSON docLink values, not an
   invented `api2` proxy or a generic `api-terms-v1.pdf` URL. A JSON-declared docLink is a
   document identity, not a proven retrieval URL; fail closed where retrieval identity is
   not retained.
3. The false claim that APIA §5.1 limits the license to "personal, non-commercial
   purposes" was removed. §5.1 grants a limited/non-exclusive/non-sublicensable/
   non-transferable/non-assignable/revocable license (no non-commercial qualifier).
   Supported §1.1/§1.2 (APIA in addition to / prevails over TOU) and §6.7 (no repackage/
   resell Service Data) / §6.9 (no commercial exploitation) retained.
4. Gates re-evaluated independently. G07 asks whether the scope *assumes*
   redistribution/commercial rights; a prohibition alone is not a failure. G08 is
   evidence-lineage only and must not fail on redistribution terms. Failures kept tied to
   actual missing evidence (G04 retention grant, G05 instruments-info capture).

## Corrections applied
- REVIEW-0116 record created.
- Legal-terms listing registered once at its actual endpoint
  `https://api.bybit.com/compliance/v1/wall/site-legal-terms` (R03B/R03H); false R01/R03
  duplication removed.
- Platform/API Terms PDF identities derived from JSON docLink / filename + internal
  Title; retrieval URLs marked "not retained" (fail closed on provenance).
- Unsupported `api2.bybit.com` proxy URLs and generic `api-terms-v1.pdf` URL removed.
- False §5.1 "personal, non-commercial" claim removed; §1.1/§1.2/§6.7/§6.9 preserved.
- Gate results: G01 PASS, G02 PASS, G03 PASS, G04 FAIL_UNKNOWN, G05 FAIL_UNKNOWN,
  G06 PASS, G07 PASS, G08 PASS. Blocking: G04, G05.
- Recommendation remains **NO_AUTHORITY** (G04 + G05 missing evidence). No
  implementation or downstream ticket authorized.
- REF-003 returned to AWAITING_REVIEW; all report/matrix/source-note/ticket/README/
  backlog/handoff references updated.
- Validated repo control, diff check, CSV shape, hashes/sizes/final statuses, PDF
  identities/page counts, and absence of unsupported URLs/quotation.
