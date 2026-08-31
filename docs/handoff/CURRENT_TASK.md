# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Grok Build - review-355 consolidated revision-candidate correction
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 355 rejects Grok's first revision-candidate source/test drop before integration or
execution. Its diagnostic constants omit the real `AcquisitionError: ` prefix and therefore
cannot classify any accepted pending row. Independent blockers remain in physical SQLite read-
only behavior, exact generation authentication, held-root safety, listing/checkpoint authority,
production boundedness/resumable failure handling, and deterministic transactional publication.

The reviewer's intended query-only confirmation empirically proved that ordinary SQLite
`mode=ro` can create or refresh `state.sqlite-shm` for this WAL database. Review 355 discloses
the incident and pins the unchanged 2,386,247,680-byte state file plus current empty WAL and
32,768-byte SHM identities. They must be preserved exactly; no cleanup or data action is
authorized. Corrected source must use an actually immutable held-descriptor snapshot and prove
zero active-tree side effects.

Sr Dev - Grok Build must correct only Review 355's same planner module, CLI, test source, and
bounded fixtures as one coherent drop. It performs no command, test, network/data operation,
real SQLite open, active-state edit, migration, Git operation, or existing acquisition-source
change, and stops for reviewer static inspection. Hermes, candidate execution, cleanup, and all
further acquisition remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/355_CEX002_GROK_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`
- `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`
