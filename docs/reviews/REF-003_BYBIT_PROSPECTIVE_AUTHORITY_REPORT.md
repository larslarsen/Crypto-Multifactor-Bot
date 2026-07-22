# REF-003 — Bybit Prospective Instrument Snapshot Authority Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_AUTHORITY
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (audited under REVIEW-0115; corrected under REVIEW-0116)
**Auditor:** Jr Dev — Hermes (Hy3:free)

## Scope
Prospective-collection authority audit for Bybit instrument snapshots. **Prospective
only.** Historical state transitions, settled events, announcements, and REF-002 G04/G05
remain blocked and out of scope. No collector, code, schema, migration, historical
reconstruction, factor, portfolio, or live work.

## Recommendation: NO_AUTHORITY (fail-closed)
Blocking gates: **G04 (unknown), G05 (unknown)**. PASS: G01, G02, G03, G06, G07, G08.

## Key findings (corrected REVIEW-0116)
- **G01 PASS:** Platform Terms v15 PDF (400,739B, 42pp, LM 2026-07-15) docLink identity
  `8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf` matches the official legal-terms listing entry
  (version 15, updateTime 2026-07-15). API Terms v1 is a distinct 7-page document
  (LM 2025-09-08, internal Title "EN - API Terms & Conditions") not in the listing.
- **G02 PASS:** APIA §1.1 applies "in addition to" TOU; §1.2 APIA prevails on
  inconsistency. Distinct and cumulative.
- **G03 PASS:** APIA §5.1 grants a limited, non-exclusive, non-sublicensable,
  non-transferable, non-assignable and revocable license to use the API; §2.2 permits
  automated query/request. Automated public-API acquisition is within the license.
- **G04 FAIL-UNKNOWN:** No explicit internal non-commercial raw-snapshot retention
  grant in either document; Bybit's 7-year clause is its own obligation.
- **G05 FAIL-UNKNOWN:** Legal-terms listing API is deterministic (ret_code 0), but no
  instruments-info (v5/market) request/response was captured; pagination/request
  identity for instruments-info is unverified.
- **G06 PASS:** Prospective semantics committed — known_from = retrieved_at only;
  knowledge is never backdated. Historical transitions explicitly out of scope.
- **G07 PASS:** G07 asks whether the proposed scope *assumes* redistribution/commercial
  rights. The prospective scope (internal non-commercial raw retention, no
  redistribution) does NOT assume those rights. A provider prohibition alone is not a
  gate failure. §6.7 (no repackage/resell of Service Data) and §6.9 (no commercial
  exploitation) are recorded as future-use constraints, not gate failures.
- **G08 PASS:** Evidence-lineage only. Immutable snapshot/version lineage established
  for both PDFs (SHA-256, version, docLink/filename identity) and the legal-terms
  listing (retained body+headers, ret_code 0). G08 does not fail on redistribution
  terms. (Retrieval URLs not retained in headers is a lineage limitation, noted.)

## Evidence provenance (corrected)
- Legal-terms listing registered against its **actual endpoint**
  `https://api.bybit.com/compliance/v1/wall/site-legal-terms` (R03B/R03H).
- Platform/API Terms PDF document identities derived from JSON docLink / filename +
  internal Title. The retained headers do **not** contain the request line, so exact
  retrieval URLs are **not retained** — fail closed on provenance (not on licensing).
- Unsupported `api2.bybit.com` proxy URLs and a generic `api-terms-v1.pdf` URL were
  removed. No false R01/R03 duplication (each row has distinct bytes/headers).
- Legacy help-page shells (R04H/R05H, HTTP 403) registered only to document the block;
  not used as terms evidence.

## Decision matrix
See `research/ref_003/decision_matrix.csv` (gates G01-G08).

## Evidence register
See `research/ref_003/EVIDENCE_REGISTER.csv` (8 rows: 2 PDF bodies + headers, legal
listing JSON body + headers at the actual endpoint, and 2 blocked legacy help-page
header rows).

## Validation performed
- path / SHA-256 / size for all 8 rows: **valid**.
- final HTTP status present in retained headers for all 5 header rows (R01H/R02H/R03H
  = 200; R04H/R05H = 403): **valid**.
- PDF identity / page count: Platform v15 = 42pp, API v1 = 7pp: **valid**.
- Absence of unsupported URLs / false §5.1 quotation: **verified**.
- `python3 scripts/check_repo_control.py`: **PASS**.
- `git diff --check`: **clean** (0 CR bytes in register).

## Note
This audit does not use the legacy help-page shell as terms evidence, does not infer
retention permission from general API access, and does not authorize any implementation
or downstream ticket. A pass would authorize only a later implementation ticket.
