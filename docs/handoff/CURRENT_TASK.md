# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - integrate exact review-361 source/test drop
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 361 accepts Sol High's exact six-path revision-candidate planner source/test/fixture drop
for bounded Hermes integration. The Review-360 lifecycle correction explicitly closes manifest
iterators while SQLite is live, and the one authorized targeted run passes all 109 cases with no
warning output. Static review confirms the complete generation/listing/checkpoint/publication/
recovery authority and boundedness contract.

Hermes must rehash and stage only the accepted paths, run Review 361's targeted pytest, targeted
ruff, repository-control, and scoped diff checks, publish record 362 with complete outputs, update
this handoff and the ticket, commit, push, prove `HEAD == origin/main`, and stop. It may not patch
developer bytes or disturb unrelated dirty paths. Real planner/network/data/acquisition/
generation-transition work remains unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket is
`NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/361_CEX002_SOL_REVISION_CANDIDATE_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`
- `research/sprint_004/360_CEX002_SOL_RECOVERY_CORRECTION_WARNING_STATIC_REJECTION.md`
- `research/sprint_004/359_CEX002_SOL_CORRECTED_REVISION_CANDIDATE_RECOVERY_STATIC_REJECTION.md`
- `research/sprint_004/358_CEX002_SOL_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/357_CEX002_SOL_HIGH_REVISION_CANDIDATE_REROUTE.md`
- `research/sprint_004/356_CEX002_GROK_SECOND_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/355_CEX002_GROK_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`
- `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`
