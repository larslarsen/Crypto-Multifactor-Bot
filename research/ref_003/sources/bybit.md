# Source note — Bybit (REF-003, prospective authority audit, corrected REVIEW-0116)

Audit target: Bybit prospective instrument-snapshot authority. Scope is **prospective
collection only**. Historical state transitions, settled events, announcements, and
REF-002 G04/G05 are **blocked and out of scope**.

## Verified evidence (retained captures)
- **Platform Terms v15** PDF: 400,739 bytes, **42 pages**, PDF 1.7, Producer WPS
  Writer / macOS 26.5.1, Last-Modified **2026-07-15**. Document identity derived from
  the retained legal-terms JSON docLink
  `/common-static/compliance/legal/BYBIT/8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`
  (version 15, updateTime 2026-07-15). **Exact retrieval URL not retained in the
  header** (fail closed on lineage).
- **API Terms v1** PDF: 137,059 bytes, **7 pages**, PDF 1.4, Producer Skia/PDF m141
  Google Docs, internal Title "EN - API Terms & Conditions", Last-Modified
  **2025-09-08**. NOT enumerated in the retained legal-terms listing (no API-Terms
  entry). Document identity = filename + internal Title only; **retrieval URL not
  retained** (fail closed).
- **Legal-terms listing JSON** (`ret_code 0`): actual endpoint
  `https://api.bybit.com/compliance/v1/wall/site-legal-terms`. Lists 10 docs; Platform
  Terms entry name `Bybit-BTL-Platform-Terms-and-Conditions`, version **15**, docLink
  `8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`, updateTime 1784101893 (2026-07-15). No
  separate "API Terms" entry enumerated. Deterministic; request identity retained.
- **Legacy help-page shells** (bybit_legal_terms*, bybit_legal_terms_service*): HTTP
  **403** (Akamai). Deliberately NOT used as terms evidence.

## Document identity vs retrieval URL
A JSON-declared docLink (e.g. `8f54e9463ad3fa8ab9c0fc25f3a.pdf`) is a **document
identity**, not a proven retrieval URL. The retained headers do not contain the
request line, so the exact retrieval URLs for the two PDFs are **not retained** —
fail closed on provenance. The listing JSON's actual endpoint IS retained.

## Version identity
Platform Terms v15 PDF Last-Modified (2026-07-15) matches the listing entry updateTime
(1784101893 = 2026-07-15) and docLink hash. API Terms v1 is a separate document.

## API Terms relationship (supported text only)
- §1.1: APIA "will apply to you in addition to our standard Terms of Use (TOU)".
- §1.2: to the extent of inconsistency, **APIA prevails** over TOU.
- §5.1: grants "a limited, non-exclusive, non-sublicensable, non-transferable,
  non-assignable and revocable license" to use the API. (No "personal, non-commercial"
  qualifier — that claim was removed as unsupported.)
- §6.7: "shall not ... repackage or resell the services, or any part thereof, API or
  Service Data."
- §6.9: "shall not commercially exploit the APIs."

## Gate re-evaluation (REVIEW-0116)
- G01 PASS (doc chain/version from JSON docLink). G02 PASS (APIA vs TOU relationship).
- G03 PASS (automated API acquisition within §5.1 license).
- G04 FAIL-UNKNOWN (no explicit internal non-commercial raw-snapshot retention grant).
- G05 FAIL-UNKNOWN (no instruments-info capture; pagination/identity unverified).
- G06 PASS (prospective known_from = retrieved_at; never backdate).
- G07 PASS: the proposed scope does NOT assume redistribution/commercial rights; a
  provider prohibition alone is not a gate failure. §6.7/§6.9 recorded as future-use
  constraints.
- G08 PASS: evidence-lineage only; established for both PDFs + listing. Does not fail
  on redistribution terms.

## Recommendation
**NO_AUTHORITY** (fail-closed) — blocked by G04 + G05 missing evidence. A pass would
authorize only a later implementation ticket; none is authorized now.
