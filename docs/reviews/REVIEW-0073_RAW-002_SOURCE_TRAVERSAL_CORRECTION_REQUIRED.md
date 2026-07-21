# REVIEW-0073 - RAW-002 SOURCE TRAVERSAL CORRECTION REQUIRED

**Ticket:** RAW-002 - Harden publication-receipt verification against symlink substitution
**Status:** CHANGES_REQUIRED - JR CONTROL PUBLICATION, THEN SR SOURCE
**Next required actor:** Jr Dev - Hermes, then Sr Dev - Sandbox
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The local source correctly constructs the expected final path without resolving it, compares the
receipt lexically, checks every root-relative component with `lstat`, and preserves shared
`canonical_identity` behavior. Source approval is withheld for one lexical-canonicality defect.

`assert_lexical_under_root` calls `normpath` before checking for `.` or `..`. Traversal components
are therefore collapsed and the subsequent rejection check cannot detect them. A receipt path such
as `<root>/raw/../raw/...` can normalize to the expected path instead of failing as noncanonical.

## Required Correction

- Reject lexical `.` and `..` components before normalization or containment comparison.
- Preserve absolute-path and under-root checks without following symlinks.
- Keep the expected lexical-path construction, component `lstat` checks, shared identity behavior,
  and all unrelated source unchanged.

The local source assignment is `docs/reviews/RAW-002_SR_SOURCE_CORRECTION_TASK.md`.
