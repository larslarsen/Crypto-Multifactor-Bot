# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Grok Build XHigh - review-330 standalone retirement tool
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Hermes integrated the exact retained-byte fixture in pushed commit `6e7ed86`, and the one
authorized targeted acquisition suite passed. Review 330 accepts the complete ADR-0030
retained-authority correction.

The rejected 742,380,087-byte Gate-2 store remains untouched. Its exact ten-entry filesystem
inventory and immutable read-only SQLite facts are bound in the review-330 authority JSON at
SHA-256 `8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1`.
It contains 737,119 plan rows, 90 retained labels, 202 gaps, one unfinished zero-fact run, and
no acquisition facts.

Grok Build XHigh must create only the standalone retirement module, CLI, and synthetic test
source named in Review 330. The tool imports no acquisition code, provides read-only `inspect`
and exact-authority `retire`, and implements held-lock, no-follow inventory, immutable SQLite
proof, `renameat2(RENAME_NOREPLACE)`, directory `fsync`/filesystem `syncfs`, and complete
post-proof. Do not run commands/tests, use Git, or touch real data. Return the three hashes and
line counts plus test-function count.

Integration, validation, real inspection/retirement, corrected planning, acquisition, later
gates, and next-ticket work remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `docs/adr/0030-exact-retained-credit-and-pre-network-plan-retirement.md`
- `research/sprint_004/330_CEX002_GATE2_RETIREMENT_TOOL_ARCHITECTURE_AND_SOURCE_AUTHORIZATION.md`
- `research/sprint_004/330_CEX002_REJECTED_GATE2_RETIREMENT_AUTHORITY.json`
