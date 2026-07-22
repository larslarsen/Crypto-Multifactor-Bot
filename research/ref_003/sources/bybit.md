# Source note — Bybit (REF-003, prospective authority audit; corrected REVIEW-0116/0117)

Audit target: Bybit prospective instrument-snapshot authority. Scope is **prospective
collection only**. Historical state transitions, settled events, announcements, and
REF-002 G04/G05 are **blocked and out of scope**.

## Verified evidence (retained captures)
- **Platform Terms v15** PDF: 400,739 bytes, **42 pages**, PDF 1.7, Producer WPS
  Writer / macOS 26.5.1, Last-Modified **2026-07-15**. Document identity derived from
  the retained legal-terms JSON docLink
  `/common-static/compliance/legal/BYBIT/8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`
  (version 15, updateTime 2026-07-15). **The retained PDF headers do NOT bind the PDF
  response to that retrieval URL** (fail closed on binding).
- **API Terms PDF artifact (UNVERIFIED official version)**: 137,059 bytes, **7 pages**,
  PDF 1.4, Producer Skia/PDF m141 Google Docs, internal Title "EN - API Terms &
  Conditions", Last-Modified **2025-09-08**. The local filename and internal title do
  **NOT** prove an official Bybit version or legal chain. Not enumerated in the retained
  legal-terms listing (no API-Terms entry). Retrieval URL NOT retained (fail closed).
- **Legal-terms listing JSON** (`ret_code 0`): actual endpoint
  `https://api.bybit.com/compliance/v1/wall/site-legal-terms`. Lists 10 docs; Platform
  Terms entry name `Bybit-BTL-Platform-Terms-and-Conditions`, version **15**, docLink
  `8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`, updateTime 1784101893 (2026-07-15). No
  separate "API Terms" entry enumerated. **The retained response header proves
  status/time only and contains NO URL**; the endpoint identity is recorded in the
  register, not proven by the header.
- **Legacy help-page shells** (bybit_legal_terms*, bybit_legal_terms_service*): HTTP
  **403** (Akamai). Deliberately NOT used as terms evidence.

## Document identity vs retrieval URL
A JSON-declared docLink is a **document identity**, not a proven retrieval URL. The
retained PDF headers do not contain the request line, so exact retrieval URLs are NOT
retained — fail closed on provenance/binding.

## API Terms relationship (supported text only)
- §1.1: APIA "will apply to you in addition to our standard Terms of Use (TOU)".
- §1.2: to the extent of inconsistency, **APIA prevails** over TOU.
- §5.1: grants "a limited, non-exclusive, non-sublicensable, non-transferable,
  non-assignable and revocable license" to use the API. (No "personal, non-commercial"
  qualifier.)
- §6.7: "shall not ... repackage or resell the services, or any part thereof, API or
  Service Data."
- §6.9: "shall not commercially exploit the APIs."

## Gate re-evaluation (REVIEW-0117)
- **G01 FAIL_UNKNOWN (blocking):** official API Terms identity/version and PDF retrieval
  binding are unproven. API Terms PDF artifact has no proven official version/legal
  chain; Platform docLink present in listing but PDF headers do not bind response to
  retrieval URL.
- G02 PASS (blocking No): content-level/conditional on captured artifact; cannot cure G01.
- G03 PASS (blocking No): content-level/conditional on captured artifact; cannot cure G01.
- **G04 FAIL_UNKNOWN (blocking):** no explicit internal non-commercial raw-snapshot
  retention grant.
- **G05 FAIL_UNKNOWN (blocking):** no instruments-info capture; pagination/identity
  unverified.
- G06 PASS (blocking No): prospective known_from = retrieved_at; never backdate.
- G07 PASS (blocking No): proposed scope does NOT assume redistribution/commercial
  rights; a provider prohibition alone is not a gate failure. §6.7/§6.9 are future-use
  constraints.
- **G08 FAIL_UNKNOWN (blocking):** evaluated against PROSPECTIVE INSTRUMENT-SNAPSHOT
  lineage, not legal-document hashes. No prospective instruments-info request, body,
  headers, pagination, hashes, status, or object-version lineage exists. Unproven.

## Recommendation
**NO_AUTHORITY** (fail-closed) — blocked by G01, G04, G05, G08. A pass would authorize
only a later implementation ticket; none is authorized now.
