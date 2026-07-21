# RAW-002 - JR FINAL ADVERSARIAL TEST TASK

**Ticket:** `tickets/RAW-002.md`
**Actor:** Jr Dev - Hermes
**Status:** INCOMPLETE - REVIEW-0076 FINAL CORRECTION REQUIRED
**Next ticket:** `NONE`

## Assignment

Replace weak RAW-002 fixtures with branch-accurate adversarial evidence required by REVIEW-0075.

## Required Tests

- Final symlink: point the canonical final path to an outside-root regular file containing the
  exact expected bytes and size. Assert `CatalogRegistrationError` and assert `_sha256_file` was
  not called.
- Parent symlink: create an outside-root target containing the complete remaining canonical fanout
  and exact object bytes, substitute the parent with a symlink, and assert rejection before hash.
- Traversal alias: use a receipt path containing `..` that lexically normalizes to the exact
  canonical path; assert traversal rejection.
- Escaping prefix: make receipt and configured prefixes agree on a traversal-containing prefix and
  provide its matching URI; assert lexical escape rejection rather than URI mismatch.
- Missing component: remove a component from the actual canonical path while retaining the exact
  canonical receipt path; assert the component-`lstat` missing failure.
- Digest: mutate the canonical regular file to different bytes of the same size and assert the
  post-path-validation SHA-256 mismatch.
- Retain non-directory-parent, non-regular-final, canonical acceptance, ID, URI, and size coverage.

Use targeted mocking only to prove `_sha256_file` is not called for substituted symlink paths; do
not mock the path-safety behavior under test.

## Acceptance Gates

Run and record all six commands from `docs/reviews/RAW-002_JR_INTEGRATION_TASK.md` exactly.

## Records And Publication

Correct `docs/reviews/RAW-002_CHANGE_REPORT.md` so tests, branch claims, file list, and exact gate
outputs match the published integration. Set the ticket and handoff to `AWAITING_REVIEW`, name
Reviewer as next actor, retain `Next ticket authorized: NONE`, update task status, commit, and push.

## Completion Condition

The published repository contains branch-accurate adversarial regressions, truthful evidence,
passing gates, and an `AWAITING_REVIEW` handoff.
