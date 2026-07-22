# REF-003 — Bybit Prospective Instrument Snapshot Authority Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_AUTHORITY
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (audited REVIEW-0115; corrected REVIEW-0116; REVIEW-0117)
**Auditor:** Jr Dev — Hermes (Hy3:free)

## Scope
Prospective-collection authority audit for Bybit instrument snapshots. **Prospective
only.** Historical state transitions, settled events, announcements, and REF-002 G04/G05
remain blocked and out of scope. No collector, code, schema, migration, historical
reconstruction, factor, portfolio, or live work.

## Recommendation: NO_AUTHORITY (fail-closed)
**Final blockers: G01, G04, G05, G08.** PASS: G02, G03, G06, G07 (G02/G03 content-level,
unable to cure G01).

## Key findings (REVIEW-0117)
- **G01 FAIL_UNKNOWN (blocking):** official API Terms identity/version and PDF retrieval
  binding are unproven. The API Terms PDF artifact has a local filename and internal
  Title but **no proven official Bybit version or legal-chain binding**. The Platform
  Terms docLink is present in the listing, but the **retained PDF headers do NOT bind
  the PDF response to that retrieval URL**.
- **G02 PASS (blocking No):** APIA §1.1 applies "in addition to" TOU; §1.2 APIA prevails
  on inconsistency. Content-level/conditional on the captured artifact; unable to cure G01.
- **G03 PASS (blocking No):** APIA §5.1 grants a limited, non-exclusive, non-sublicensable,
  non-transferable, non-assignable and revocable license to use the API; §2.2 permits
  automated query/request. Content-level/conditional on the captured artifact; unable to
  cure G01.
- **G04 FAIL_UNKNOWN (blocking):** No explicit internal non-commercial raw-snapshot
  retention grant in either document; Bybit's 7-year clause is its own obligation.
- **G05 FAIL_UNKNOWN (blocking):** Legal-terms listing API is deterministic (ret_code 0),
  but no instruments-info (v5/market) request/response was captured; pagination/request
  identity for instruments-info is unverified.
- **G06 PASS (blocking No):** Prospective semantics committed — known_from = retrieved_at
  only; knowledge is never backdated. Historical transitions explicitly out of scope.
- **G07 PASS (blocking No):** G07 asks whether the proposed scope *assumes*
  redistribution/commercial rights. The prospective scope does NOT assume those rights.
  A provider prohibition alone is not a gate failure. §6.7/§6.9 recorded as future-use
  constraints.
- **G08 FAIL_UNKNOWN (blocking):** evaluated against **prospective instrument-snapshot
  lineage**, not legal-document hashes. **No prospective instruments-info request, body,
  headers, pagination, hashes, status, or object-version lineage exists.** Therefore the
  instrument-snapshot lineage is unproven.

## Evidence provenance
- Legal-terms listing registered at its actual endpoint
  `https://api.bybit.com/compliance/v1/wall/site-legal-terms` (R03B/R03H). **The retained
  response header proves status/time only and contains NO URL**; the endpoint identity is
  recorded in the register, not proven by the header.
- Platform/API Terms PDF document identities derived from JSON docLink / filename +
  internal Title. The retained headers do **not** contain the request line, so exact
  retrieval URLs are **not retained** — fail closed on provenance/binding.
- API Terms PDF renamed to unverified **"API Terms PDF artifact"**; official version set to
  **UNPROVEN** (local filename + internal Title do not prove an official Bybit version or
  legal chain).
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
- PDF identity / page count: Platform v15 = 42pp, API artifact = 7pp: **valid**.
- `python3 scripts/check_repo_control.py`: **PASS** (state AWAITING_REVIEW).
- `git diff --check`: **clean** (0 CR bytes in register).

## Note
This audit does not use the legacy help-page shell as terms evidence, does not infer
retention permission from general API access, and does not authorize any implementation
or downstream ticket. A pass would authorize only a later implementation ticket.
