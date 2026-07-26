# REVIEW-0219 — ARCH-003 Changes Required

## Verdict

**CHANGES REQUIRED**

ARCH-003 remains routed to Sr Dev Grok Build. ADR-0015 remains Proposed. No
acceptance is granted and no production source changes are made by this record.

## Required Sr Dev Corrections

1. Remove fabricated 2017 listing dates; use evidence-backed dates or explicitly
   labeled first-bar proxies.
2. Model asset, token contract, pool legs, venue listing, and canonical integer
   surrogate separately.
3. Replace global database access and integer-cast catalog IDs with an explicit
   resolver.
4. Centralize valid-time plus knowledge-time listing lifecycle logic.
5. Bind experiments to immutable published universe datasets, not mutable SQLite
   tables.
6. Remove identity resolution from raw acquisition without deleting the
   normalization/publication path.
7. Remove mutable symbol-registry membership.
8. Preserve case-sensitive Solana addresses.
9. Wire all experiment and paper entrypoints to the new binding.

## Handoff

- **Ticket:** ARCH-003
- **Status:** READY
- **Next required actor:** Sr Dev — Grok Build
- **Next ticket authorized:** NONE
- **Tests run:** No
- **Production source modified:** No
