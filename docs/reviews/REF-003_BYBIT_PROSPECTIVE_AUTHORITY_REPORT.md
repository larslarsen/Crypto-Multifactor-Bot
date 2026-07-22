# REF-003 — Bybit Prospective Instrument Snapshot Authority Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_AUTHORITY
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (audited under REVIEW-0115)
**Auditor:** Jr Dev — Hermes (Hy3:free)

## Scope
Prospective-collection authority audit for Bybit instrument snapshots. **Prospective
only.** Historical state transitions, settled events, announcements, and REF-002 G04/G05
remain blocked and out of scope. No collector, code, schema, migration, historical
reconstruction, factor, portfolio, or live work.

## Recommendation: NO_AUTHORITY (fail-closed)
Blocking gates: **G04 (unknown), G05 (unknown), G07 (FAIL), G08 (partial)**.
G01 (doc chain/version), G02 (API vs Platform applicability), G03 (automated API
acquisition), G06 (prospective known-time semantics) PASS.

## Key findings
- **G01 PASS:** Platform Terms v15 PDF (400,739B, 42pp, LM 2026-07-15) matches the
  official legal-terms listing entry (version 15, docLink `8f54e9463ad3fa8ab9c0a39c0fc25f3a.pdf`,
  updateTime 2026-07-15). API Terms v1 is a distinct 7-page document (LM 2025-09-08).
- **G02 PASS:** API Terms (APIA) apply "in addition to" Platform Terms; the two are
  distinct and cumulative.
- **G03 PASS:** APIA s5 grants a revocable license "to use the API"; s2.2 permits
  automated query/request. Automated public-API acquisition is within the license.
- **G04 FAIL-UNKNOWN:** No explicit internal non-commercial raw-snapshot retention
  grant in either document; Bybit's 7-year clause is its own obligation, not a user grant.
- **G05 FAIL-UNKNOWN:** Legal-terms listing API is deterministic (ret_code 0), but no
  instruments-info (v5/market) request/response was captured; pagination/request
  identity for instruments-info is unverified.
- **G06 PASS:** Prospective semantics committed — known_from = retrieved_at only;
  knowledge is never backdated. Historical transitions explicitly out of scope.
- **G07 FAIL:** Platform Terms bar "commercial use of the Site or Platform" and
  "scraping"; APIA s6.9 bars "commercially exploit the APIs" and s5 bars "repackage or
  resell ... Service Data". No redistribution/commercial-use assumption permitted.
- **G08 FAIL-PARTIAL:** Immutable snapshot/version lineage established for both PDFs
  (SHA-256, version, docLink) and the legal-terms listing; but G07 bars redistribution,
  so publish/retain-distribute authority is incomplete.

## Decision matrix
See `research/ref_003/decision_matrix.csv` (gates G01-G08).

## Evidence register
See `research/ref_003/EVIDENCE_REGISTER.csv` (8 rows: PDF bodies + headers, API JSON
body + headers, and two blocked legacy help-page header rows registered only to
document the 403 block; not used as terms evidence).

## Validation performed
- path / SHA-256 / size for all 8 rows: **valid**.
- final HTTP status present in retained headers for all 5 header rows (R01H/R02H/R03H
  = 200; R04H/R05H = 403): **valid**.
- PDF identity / page count: Platform v15 = 42pp, API v1 = 7pp: **valid**.
- `python3 scripts/check_repo_control.py`: **PASS**.
- `git diff --check`: **clean** (0 CR bytes in register).

## Note
This audit does not use the legacy help-page shell as terms evidence, does not infer
retention permission from general API access, and does not authorize any implementation
or downstream ticket. A pass would authorize only a later implementation ticket.
