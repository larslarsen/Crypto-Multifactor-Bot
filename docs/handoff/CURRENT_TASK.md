# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Claude Build - review-356 revision-candidate correction
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 356 rejects Grok's second revision-candidate source/test drop before integration or
execution. The correction now has exact diagnostics, held immutable SQLite access, stronger
generation binding, an on-disk listing index, resumable transport handling, deterministic gzip,
and a locator commit direction. Those corrections are preserved.

Residual authority blockers remain. The claimed stable second pass merely reparses the first
pass's retained bytes and makes no independent listing request. Exact final response URLs,
headers, retrieval clocks, and mandatory single-part sidecar ETags are not bound. Checkpoint
completion/reachability can still be forged, unsafe checkpoint/locator leaves can be treated as
absent, and live page bounds are not enforced. Generation proof lacks the explicit read
transaction and exact pending/charge predicates; root binding remains exposed before held opens.
Completed-locator recovery does not authenticate the manifest or lineage, and publication tests
do not reach the asset-to-locator boundaries.

After two Grok authority misses, the repository routing policy rotates this bounded correction
to Sr Dev - Claude Build using Claude Opus 5. Claude may edit only Review 356's same planner,
mechanically necessary CLI, test source, and bounded fixtures. It may run exactly one enumerated
temporary-rooted targeted pytest command after editing, then stops with its output and exact
identities for reviewer static inspection. It performs no other command, network/data action,
real-state access, planner, integration, records, or Git. Hermes and all further acquisition
remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/356_CEX002_GROK_SECOND_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/355_CEX002_GROK_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`
- `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`
