# REVIEW-0072 - RAW-002 SR SOURCE AUTHORIZED

**Ticket:** RAW-002 - Harden publication-receipt verification against symlink substitution
**Status:** JR CONTROL PUBLICATION, THEN SR SOURCE
**Next required actor:** Jr Dev - Hermes, then Sr Dev - Sandbox
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

RAW-002 is authorized. `verify_publication_receipt` currently resolves both its expected canonical
path and the receipt path before comparing them. A final-path symlink substituted after publication
can therefore resolve to the same target and disappear from subsequent symlink checks.

## Approved Contract

- Resolve and validate the configured store root once.
- Derive the digest, object ID, relative content-addressed path, and storage URI canonically.
- Construct the expected absolute path lexically from the resolved root plus canonical relative
  path; do not resolve the expected final path.
- Prove the lexical expected path remains under the configured root.
- Compare the receipt path to the expected lexical path without following symlinks.
- Inspect every root-relative path component with `lstat`; reject missing components, symlinks,
  non-directory parents, and a non-regular final component before any content read.
- Only after path checks, verify byte size and SHA-256 as before.
- Surface stable `CatalogRegistrationError` failures and preserve canonical ID/URI behavior.

Keep the shared `canonical_identity` behavior unchanged unless a separately named lexical helper is
needed; RAW-002 must not silently alter all existing writer/path callers. Concurrent filesystem
mutation after verification begins remains outside this defense-in-depth ticket.

The local source assignment is `docs/reviews/RAW-002_SR_SOURCE_TASK.md`.
