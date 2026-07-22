# Source authority note — Point-in-time on-chain observation (DF-07 synthesis)

Synthesis target: whether accepted repository evidence authorizes point-in-time on-chain
observations (blocks, addresses, fees, and the required known-block publication/revision audit
test). Evidence synthesis only; no new factual inference.

## What is repository-native (used here)
Fifteen accepted artifacts (paths/hashes/sizes in `EVIDENCE_REGISTER.csv`): sprint_002/06 and
NET-01 addendum; sprint_003/01 decision register, 02 object inventory, 03 schema/semantics,
05 correction/revision audit, 08 research data decisions, 13 research lead decisions, audit
reconciliation + hash verification, Coin Metrics source note; REVIEW-0008 AUD-003 final; and
the accepted DF-01 ticket/matrix/REVIEW-0124. No prior accepted evidence artifact was modified.

## Three timestamps must be distinguished
- **Block/event timestamp**: the on-chain time of the block/transaction/event itself.
- **Provider/indexer publication timestamp**: when an indexer or API published/served the observation.
- **Repository retrieval timestamp**: when the accepted metadata/catalog was captured into the repo.
The accepted inventory records bounded observations and catalog/metadata; original API response
bodies are NOT repository-retained, so only retrieval-time metadata (and stored retrieval
timestamps where recorded) are available — block/event vs publication/known time is not resolved.

## Preserved exact boundaries
- SRC-006 observations/catalog accepted REFERENCE_METADATA; NET-01 use remains conditional.
- Coin Metrics Community CONDITIONAL — EXPLORATORY_PHASE2.
- SRC-006b CONDITIONAL (publication-time/revision unbounded).
- SRC-010 CONDITIONAL and was not queried.
- RD-05 conditional finding/next action, not authority.
- RD-07 does not override source-specific conditions or authorize on-chain data.
- DF-01 accepted NO_PRIMARY_PIT_SUPPLY_AUTHORITY; does not resolve DF-07.

## Gate results (all blocking; authority requires all eight PASS)
- G01 FAIL_UNKNOWN: no accepted source grants on-chain blocks/addresses/fees authority (SRC-010 CONDITIONAL/not queried; Coin Metrics reference metadata; DF-01 no supply authority).
- G02 FAIL_UNKNOWN: on-chain metric semantics, chain mappings, entity/spam treatment unestablished.
- G03 FAIL_UNKNOWN: block/event time vs indexer publication/known time not resolved (SRC-010 differs, not queried).
- G04 FAIL_UNKNOWN: on-chain revisions/backfills unbounded (SRC-010 none recorded; SRC-006b CONDITIONAL); no vintage preservation retained.
- G05 FAIL_UNKNOWN: chain/asset/metric coverage and archival depth not established (SRC-010 not queried; Coin Metrics limited).
- G06 FAIL_UNKNOWN: retained artifacts are catalog/metadata with hashes; original API bodies not retained; no raw on-chain provenance.
- G07 FAIL_UNKNOWN: SRC-010 separate procurement (keys/limits); Coin Metrics CONDITIONAL; licensing unestablished/ambiguous.
- G08 FAIL_BLOCKED: required known-block publication/revision audit test NOT executed (SRC-010 not queried; AUD-003 no on-chain test). Hard blocker.

## Decision
`NO_POINT_IN_TIME_ON_CHAIN_OBSERVATION_AUTHORITY`. No NET-01, DIL-01, collection, procurement,
implementation, schema, tests, or next ticket authorized.
