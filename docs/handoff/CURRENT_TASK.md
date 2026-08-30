# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-350 corrected acquisition continuation
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 350 accepts Hermes's safe preproof stop and corrects its false-negative query. Record
349 counted 30,266 cumulative terminal attempt rows, while Review 348 required 27,658 distinct
pending identities. The extra 2,608 rows are the prior run's attempts for the same identities.
Reviewer query-only inspection proves the receipt, state, sidecars, completions, gaps, charges,
runs, and seals remain exactly unchanged; all three acquisition invocations remain unused.

Hermes must follow Review 350's corrected latest-terminal-per-identity preproof and then Review
348's unchanged bounded acquisition contract. With external-network escalation, run up to
three sequential 84,600-second engine sessions and apply every exact continuation predicate
after each. Exit 3, exit-2 `partial`, any new blocker, or the third invocation ends the
campaign. Publish only record 351 and stop. Do not repair or dispose revision objects, run a
fourth acquisition, replay, or invoke `verify`. Later gates and next-ticket work remain
unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/350_CEX002_PREPROOF_FALSE_NEGATIVE_AND_CONTINUATION.md`
- `research/sprint_004/349_CEX002_BOUNDED_ACQUISITION_CONTINUATION.md`
- `research/sprint_004/348_CEX002_CAMPAIGN_BLOCKER_REVIEW_AND_CONTINUATION.md`
