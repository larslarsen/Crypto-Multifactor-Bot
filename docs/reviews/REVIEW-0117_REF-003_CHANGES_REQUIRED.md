# REVIEW-0117 — REF-003 CHANGES REQUIRED

**Reviewed commit:** 28a6b5481ba559de9109ab8a87b635a597be4d8e
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Findings
- **G01 must be blocking FAIL_UNKNOWN:** official API Terms identity/version and PDF
  retrieval binding are unproven. The API Terms PDF artifact has no proven official
  Bybit version or legal-chain binding; the Platform Terms PDF retrieval is not bound to
  its docLink by the retained headers.
- **G08 must be blocking FAIL_UNKNOWN:** no prospective instruments-info request, body,
  headers, pagination, hashes, status, or object-version lineage exists. G08 must be
  evaluated against prospective instrument-snapshot lineage, not legal-document hashes.
- **The listing response header contains no request URL:** do not claim endpoint identity
  is retained in headers. The listing endpoint is recorded in the register, but the
  retained response header proves status/time only and contains no URL.
- **Recommendation remains NO_AUTHORITY.**
- **Next ticket authorized:** NONE.

## Authorized corrections (COMMIT 2 scope)
Apply exact matrix results: G01 FAIL_UNKNOWN (blocking), G02 PASS (blocking No),
G03 PASS (blocking No), G04 FAIL_UNKNOWN (blocking), G05 FAIL_UNKNOWN (blocking),
G06 PASS (blocking No), G07 PASS (blocking No), G08 FAIL_UNKNOWN (blocking).
Final blockers: G01, G04, G05, G08. Rename API Terms evidence to unverified
"API Terms PDF artifact"; set official version UNPROVEN. State Platform docLink present
in listing but PDF headers do not bind the PDF response to that retrieval URL. Return
REF-003 to AWAITING_REVIEW.
