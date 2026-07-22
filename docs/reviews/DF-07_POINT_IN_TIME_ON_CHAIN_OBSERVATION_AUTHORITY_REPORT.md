# DF-07 — Point-in-Time On-Chain Observation Authority Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_POINT_IN_TIME_ON_CHAIN_OBSERVATION_AUTHORITY
**Priority:** P1
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Authorized under:** REVIEW-0135

## Objective
Determine whether accepted repository evidence authorizes point-in-time on-chain observations
(blocks, addresses, fees, and the required known-block publication/revision audit test).
Evidence synthesis only.

## Three timestamps distinguished
- **Block/event timestamp**: on-chain time of the block/transaction/event.
- **Provider/indexer publication timestamp**: when an indexer/API published/served the observation.
- **Repository retrieval timestamp**: when the accepted metadata/catalog was captured into the repo.
The accepted inventory records bounded observations and catalog/metadata; original API response
bodies are NOT repository-retained, so block/event vs publication/known time is not resolved.

## Gate results (8, all blocking — authority requires all eight PASS)
- **G01 FAIL_UNKNOWN** (blocking Yes) — no accepted source grants on-chain blocks/addresses/fees authority (SRC-010 CONDITIONAL/not queried; Coin Metrics reference metadata; DF-01 no supply authority).
- **G02 FAIL_UNKNOWN** (blocking Yes) — on-chain metric semantics, chain mappings, entity/spam treatment unestablished.
- **G03 FAIL_UNKNOWN** (blocking Yes) — block/event time vs indexer publication/known time not resolved (SRC-010 differs, not queried).
- **G04 FAIL_UNKNOWN** (blocking Yes) — on-chain revisions/backfills unbounded (SRC-010 none recorded; SRC-006b CONDITIONAL); no vintage preservation retained.
- **G05 FAIL_UNKNOWN** (blocking Yes) — chain/asset/metric coverage and archival depth not established (SRC-010 not queried; Coin Metrics limited, Issued != float).
- **G06 FAIL_UNKNOWN** (blocking Yes) — retained artifacts are catalog/metadata with hashes; original API bodies not retained; no raw on-chain provenance (request identity/version/retrieval time).
- **G07 FAIL_UNKNOWN** (blocking Yes) — SRC-010 requires separate procurement (keys/limits); Coin Metrics Community CONDITIONAL — EXPLORATORY_PHASE2; licensing unestablished/ambiguous.
- **G08 FAIL_BLOCKED** (blocking Yes) — required known-block publication/revision audit test NOT executed (SRC-010 not queried; AUD-003 bounded observations without running the test). Hard blocker.

## Decision
`NO_POINT_IN_TIME_ON_CHAIN_OBSERVATION_AUTHORITY`.

## Preserved exact boundaries
- SRC-006 observations/catalog accepted REFERENCE_METADATA; NET-01 use remains conditional.
- Coin Metrics Community CONDITIONAL — EXPLORATORY_PHASE2.
- SRC-006b CONDITIONAL (publication-time/revision unbounded).
- SRC-010 CONDITIONAL and was not queried.
- RD-05 conditional finding/next action, not authority.
- RD-07 does not override source-specific conditions or authorize on-chain data.
- DF-01 accepted NO_PRIMARY_PIT_SUPPLY_AUTHORITY; does not resolve DF-07.

## Evidence provenance
Fifteen repository-native accepted artifacts used (paths/hashes/sizes in `EVIDENCE_REGISTER.csv`):
sprint_002/06 + NET-01 addendum; sprint_003/01–03/05/08/13 + reconciliation/hash verification +
Coin Metrics note; REVIEW-0008 AUD-003 final; accepted DF-01 ticket/matrix/REVIEW-0124. No prior
accepted evidence artifact was modified. Original API response bodies are not repository-retained;
only bounded observations/catalog/metadata are accepted.

## No-authority scope
No NET-01, DIL-01, collection, procurement, implementation, schema, tests, or next ticket authorized.

## Validation
- Repo control: PASS; `git diff --check`: clean.
- Evidence register: 15 rows, hashes/sizes verified; 0 CR bytes.
- Decision matrix: 8 gates, all blocking, as specified.
- Allowed-file scope only; no gate results or historical accepted records altered.
