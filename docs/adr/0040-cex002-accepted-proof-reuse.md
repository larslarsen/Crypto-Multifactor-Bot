# ADR 0040 — Reuse the accepted proof for the known admitted CEX-002 release

Status: Accepted
Ticket: CEX-002
Reviewer: Lead Quantitative Finance Researcher/Engineer
Extends: ADR-0037 / ADR-0039, for the exact already admitted release only

## Problem

The complete Nautilus roundtrip passed for 1,165,116,869 rows. Initial catalog
admission also passed. Generic publication/replay/read-release currently recompute
the typed value digest for every source row, although the accepted proof already
binds those values to exact physical source hashes. The real replay spent nine
hours revalidating values and then stopped at its late capacity guard. Repeating
that work neither creates a new consumer proof nor changes the admitted identity.
Changing the original producer/catalog modules would invalidate their frozen runtime
source binding to the candidate. Preserve those modules and the accepted release.

## Decision

Add one external research reconciliation command for the exact accepted consumer
proof, candidate and already admitted publication. It cannot prepare or admit any
new release and cannot be used with arbitrary proof/candidate/publication pins.
Trust is anchored in the reviewer's fixed accepted proof SHA256, not a caller's
verified flag, status token, mutable cache, filename or mtime alone.

Authenticate complete proof bytes against that fixed SHA256. Authenticate candidate,
publication, every manifest and original three runtime sources; reconcile the full
strict v1 proof/manifest component set. Freshly hash every referenced physical file,
check actual table footers/schema/rows and bind safe file identities. Equality of
current source bytes to the source hashes authenticated by the accepted full proof
preserves that proof's value/time evidence. Do not decode logical table rows again.
Do not construct a new consumer proof, fabricate new readback values or claim a new
Nautilus run. Metadata remains zero observations. Changed source/proof bytes fail.

For the admitted release only, replay its no-op transaction decision using the
original catalog classification, quarantine checks and file rechecks under
BEGIN IMMEDIATE, then ROLLBACK the identical case. Any absent, partial or conflicting
catalog state fails; do not insert, update, delete or repair rows. Follow with the
original classification/consumability checks under an independent read-only snapshot
of the same publication. Reconcile all persisted columns/files/dependencies and
prove complete before/after catalog identity, including bookkeeping timestamps.
This supplies narrowly scoped known-release replay/readback evidence; it is not a
successful rerun of the previously failed publish CLI or a replacement generic API.

Check unchanged resource/reserve guards before expensive work and again before the
transaction. Preserve the original strong file-change checks at the transaction
boundary. Emit periodic measured progress and enforce a bounded execution deadline.
No changes to accepted data, source authority, economics, schemas, digest/proof
contracts, default resolver visibility or the generic publication/reader behavior.

## Acceptance boundary

For this exact admitted release, the accepted full consumer proof plus complete
fresh physical/schema/catalog authentication can satisfy the remaining committed-
release replay/readback requirement after actual successful execution and reviewer
inspection. The old capacity-failed replay remains failed evidence. Remaining
independent economic examples and final acceptance commands/report are still required.
No execution is authorized by this ADR alone; Review522 governs source and a later
explicit Hermes assignment governs validation, integration and one bounded real run.
