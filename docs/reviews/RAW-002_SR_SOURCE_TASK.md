# RAW-002 - SR PRODUCTION SOURCE TASK

**Ticket:** `tickets/RAW-002.md`
**Actor:** Sr Dev - Sandbox
**Status:** AUTHORIZED AFTER CONTROL PUBLICATION - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Implement REVIEW-0072's lexical, no-follow publication-receipt verification.

## Required Behavior

- Build the expected receipt path lexically under the resolved store root.
- Compare lexical canonical identity before following any receipt or final-path symlink.
- Use `lstat` on every component at or below the store root and reject symlinks or invalid component
  types before hashing.
- Reject canonical paths that lexically escape the store root.
- Preserve receipt completeness, object-prefix, object-ID, URI, size, and digest validation.
- Keep `canonical_identity` semantics and unrelated writer/catalog behavior unchanged.
- Convert path-safety and filesystem failures to stable `CatalogRegistrationError` results.

## Scope

Local production source only in the existing raw-ingest path/catalog modules. Reviewer inspects the
local source drop; Jr Dev - Hermes owns tests, integration, records, commit, and push after source
approval.

## Completion Condition

Complete the minimal local source correction for reviewer inspection.
