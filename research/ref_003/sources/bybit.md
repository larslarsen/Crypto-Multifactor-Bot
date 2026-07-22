# Source note — Bybit (REF-003, prospective authority audit)

Audit target: Bybit prospective instrument-snapshot authority. Scope is **prospective
collection only**. Historical state transitions, settled events, announcements, and
REF-002 G04/G05 are **blocked and out of scope**.

## Verified evidence (retained captures)
- **Platform Terms v15** PDF: 400,739 bytes, **42 pages**, PDF 1.7, Producer WPS
  Writer / macOS 26.5.1, Last-Modified **2026-07-15**. docLink
  `/common-static/compliance/legal/BYBIT/8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`.
- **API Terms v1** PDF: 137,059 bytes, **7 pages**, PDF 1.4, Producer Skia/PDF m141
  Google Docs, Title "EN - API Terms & Conditions", Last-Modified **2025-09-08**.
  Distinct document from Platform Terms.
- **Legal-terms listing API** JSON (`ret_code 0`): lists 10 docs; Platform Terms entry
  name `Bybit-BTL-Platform-Terms-and-Conditions`, version **15**, docLink
  `8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`, updateTime 1784101893 (2026-07-15). No
  separate "API Terms" entry is enumerated. Deterministic; request identity retained.
- **Legacy help-page shells** (bybit_legal_terms*, bybit_legal_terms_service*): HTTP
  **403** (Akamai). Deliberately NOT used as terms evidence (instruction: do not use
  the old unsupported help-page shell).

## Version identity
Platform Terms v15 PDF Last-Modified (2026-07-15) matches the listing entry updateTime
(1784101893 = 2026-07-15) and docLink hash. API Terms v1 is a separate document.

## Licensing findings (fail-closed)
- Automated public-API acquisition is permitted (APIA s5 revocable license to use the
  API; s2.2 query/request). → G03 PASS.
- **No redistribution / commercial use:** Platform Terms bar "commercial use of the
  Site or Platform" and "scraping"; APIA s6.9 bars "commercially exploit the APIs" and
  s5 bars "repackage or resell ... Service Data". → G07 FAIL.
- **No explicit internal non-commercial raw-snapshot retention grant.** The 7-year
  clause is Bybit's own obligation. → G04 FAIL-UNKNOWN.
- No instruments-info (v5/market) capture; pagination/request identity unverified. →
  G05 FAIL-UNKNOWN.

## Recommendation
**NO_AUTHORITY** (fail-closed). A pass would authorize only a later implementation
ticket; none is authorized now.
