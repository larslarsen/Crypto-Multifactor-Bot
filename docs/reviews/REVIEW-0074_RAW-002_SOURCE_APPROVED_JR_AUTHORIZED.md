# REVIEW-0074 - RAW-002 SOURCE APPROVED; JR INTEGRATION AUTHORIZED

**Ticket:** RAW-002 - Harden publication-receipt verification against symlink substitution
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The local RAW-002 source is approved for Jr integration. Receipt verification now constructs the
expected canonical path lexically, rejects noncanonical receipt paths before following symlinks,
checks root-relative components with `lstat`, rejects symlink/non-directory/non-regular components,
and performs size/hash reads only after path validation.

Traversal tokens are rejected before normalization, and shared `canonical_identity` behavior remains
unchanged. Concurrent mutation after verification begins remains outside this defense-in-depth
ticket as authorized by REVIEW-0072.

Jr Dev - Hermes owns tests, integration, records, commit, and push under
`docs/reviews/RAW-002_JR_INTEGRATION_TASK.md`.

## Required Integration Evidence

- Replace a canonical final object with a symlink after publication and prove receipt verification
  rejects it before target hashing.
- Replace a canonical parent component with a symlink and prove rejection.
- Reject a receipt path containing lexical `..`, an escaping prefix/path, missing components,
  non-directory parents, and a non-regular final component.
- Preserve canonical receipt acceptance plus ID, URI, size, and digest failures.
- Verify stable `CatalogRegistrationError` behavior and unchanged shared identity callers.
- Run all acceptance gates and record exact evidence.
