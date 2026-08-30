# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-348 bounded acquisition continuation
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 348 accepts Hermes's one Review-346 campaign invocation as safe bounded progress: it
added 268,437 checksum-verified Binance completions and 2,859,665,835 listed bytes, then stopped
correctly on a new checksum-mismatch message and a retry that ended in a pending metrics-size
revision rather than a completion. Reviewer read-only correction supplies record 347's omitted
family, revision-evolution, retry, and physical-hash reconciliation. All 27,658 terminal
identities are sidecar-only pending `daily/metrics` revisions; none is coverage or a gap.

Hermes must follow Review 348 exactly: with external-network escalation, run up to three
sequential 84,600-second engine sessions, applying the exact receipt, three-message metrics-
revision, retry, progress, capacity, Coinalyze, physical-artifact, and secret stop predicates
after each. Exit 3, exit-2 `partial`, any new blocker, or the third invocation ends the
campaign. Publish only record 349 and stop. Do not repair or dispose the revised metrics
objects, run a fourth acquisition, replay, or invoke `verify`. Later gates and next-ticket work
remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/348_CEX002_CAMPAIGN_BLOCKER_REVIEW_AND_CONTINUATION.md`
- `research/sprint_004/347_CEX002_BOUNDED_ACQUISITION_CAMPAIGN.md`
- `research/sprint_004/346_CEX002_NETWORK_PROGRESS_ACCEPTANCE_AND_BOUNDED_CAMPAIGN.md`
