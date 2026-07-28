# REVIEW-0253 - EXP-009 CHANGES REQUIRED

**Decision:** CHANGES_REQUIRED
**Reviewer:** Sol 5.6 High

## Findings

1. **Critical - frozen runtime economics remain overrideable.** `EXP009Runner` accepts
   arbitrary fee, slippage, weight, leverage, initial-cash, bootstrap-count, and
   block-length values, then uses several of them in the paper loop while the artifact
   and experiment fingerprint still claim the signed constants. Enforce every material
   runtime control in `__post_init__` (or remove the override surface).
2. **Critical - terminal holdout evidence still trusts caller-supplied statistics.**
   `_require_accept_evidence` checks the supplied bootstrap p-value but does not
   recompute it from the session's weekly returns. A fabricated p-value can therefore
   produce an `ACCEPT` artifact. Both `ACCEPT` and `REJECT` are terminal scientific
   verdicts and must require the exact 26-period session, recomputed frozen bootstrap,
   matching total return, complete binding series, and compliant risk evidence.
3. **High - code identity does not cover a dirty source tree.** Matching a declared SHA
   to `git HEAD` still labels uncommitted executing code as the committed tree. Require
   the artifact-determining source closure to be clean, using the established ARCH/DATA
   identity helper pattern.
4. **Medium - exact holdout timestamps are normalized rather than verified.**
   `require_holdout_calendar_timestamps` replaces hour/minute/second with midnight, so
   noon observations on the right dates pass the signed Friday-00:00 calendar. Compare
   UTC instants exactly without truncation.

Dataset/universe pin enforcement, expanded fingerprint controls, Monte Carlo correction,
calendar count, and false-ACCEPT structural requirements are otherwise corrected. The
duplicate CLI assertion is non-blocking and requires no edit.

## Required pass

Grok 4.5 should implement only the four corrections above and self-review all terminal
verdict paths once. Opus 5 performs engineering pre-review; Sol 5.6 High performs one
final quantitative acceptance review. No real holdout run, promotion, or LIVE work.

No Git or tests were run by the reviewer.

## Next

- **Next required actor:** Sr Dev - Grok 4.5
- **Engineering pre-review:** Opus 5
- **Final reviewer:** Sol 5.6 High
