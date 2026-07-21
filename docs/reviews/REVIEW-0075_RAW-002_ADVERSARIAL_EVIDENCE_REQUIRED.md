# REVIEW-0075 - RAW-002 ADVERSARIAL EVIDENCE REQUIRED

**Ticket:** RAW-002 - Harden publication-receipt verification against symlink substitution
**Status:** RESOLVED - ACCEPTED BY REVIEW-0077
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The approved source remains valid, but final acceptance is withheld because several new tests do
not exercise the security branches they claim.

## Findings

- The final symlink points to different-size/different-content bytes, so legacy verification could
  reject on size rather than prove symlink rejection.
- The parent symlink target omits the remaining canonical fanout directory, so the followed path is
  missing rather than a valid substituted object.
- The `..` fixture normalizes to a different path, not the canonical receipt path.
- The escaping-prefix test supplies only a bad storage URI while retaining a safe configured
  prefix, so URI validation rejects before lexical escape handling.
- The missing-component fixture uses a noncanonical receipt path, so identity comparison rejects
  before component `lstat`.
- No assertion proves the substituted target is rejected before `_sha256_file` is invoked.
- The change report lists `writer.py` as changed although the RAW-002 helpers are not used there;
  the submitted file list must match the actual integration.

No production-source changes are authorized. Jr Dev - Hermes owns the test/evidence correction
under `docs/reviews/RAW-002_JR_FINAL_TEST_TASK.md`.
